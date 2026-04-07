import json
import faiss
import numpy as np
from pathlib import Path
from nomic import embed, login
from sentence_transformers import CrossEncoder
from sklearn.metrics.pairwise import cosine_similarity

# -------------------------------
# Configuration
# -------------------------------
EMBEDDINGS_FILE = "chunk_embeddings.json"
EMBED_MODEL = "nomic-embed-text-v1"
TOP_K_RETRIVAL = 30  
TOP_K_FINAL = 5
MMR_LAMBDA = 0.5     

# -------------------------------
# Initialization
# -------------------------------
NOMIC_API_KEY = "nk-OJ9AEZTjD05CvxwW8f1iKynFdZySGrDHbYINcO6nj1E"
login(NOMIC_API_KEY)

print("⏳ Loading Reranker model...")
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
print("✅ Reranker ready")

# -------------------------------
# Load Data & Metadata
# -------------------------------
def load_chunks():
    with open(EMBEDDINGS_FILE, "r", encoding="utf-8") as f:
        records = json.load(f)

    chunk_data = []
    vectors = []

    for doc in records:
        source_name = doc.get("source", "Unknown Document")
        for chunk in doc["chunks"]:
            # MODIFICATION: Match keys to your new 'Gliclazide' JSON structure
            chunk_data.append({
                "text": chunk["text"],
                "source": source_name,
                "section": chunk.get("section_header", "General"), # Updated key
                "embedding": chunk["embedding"] 
            })
            vectors.append(chunk["embedding"])

    return chunk_data, np.array(vectors).astype("float32")

def build_faiss_index(vectors: np.ndarray):
    dim = vectors.shape[1]
    faiss.normalize_L2(vectors)
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    return index

def embed_query(query: str) -> np.ndarray:
    # Nomic search_query is specialized for RAG retrieval tasks
    response = embed.text(texts=[query], model=EMBED_MODEL, task_type="search_query")
    query_vec = np.array(response["embeddings"]).astype("float32")
    faiss.normalize_L2(query_vec)
    return query_vec

# -------------------------------
# MMR Diversity Logic (Prevents Redundancy)
# -------------------------------
def maximal_marginal_relevance(query_embedding, chunk_embeddings, lambda_param=0.5, k=5):
    if len(chunk_embeddings) == 0:
        return []
    
    selected_indices = []
    remaining_indices = list(range(len(chunk_embeddings)))
    
    similarities_to_query = cosine_similarity(query_embedding, chunk_embeddings)[0]
    most_relevant = np.argmax(similarities_to_query)
    selected_indices.append(most_relevant)
    remaining_indices.remove(most_relevant)
    
    while len(selected_indices) < k and remaining_indices:
        mmr_scores = []
        for idx in remaining_indices:
            relevance = similarities_to_query[idx]
            redundancy = max([cosine_similarity([chunk_embeddings[idx]], 
                             [chunk_embeddings[s]])[0][0] for s in selected_indices])
            
            # MMR Formula: lambda * relevance - (1 - lambda) * redundancy
            score = lambda_param * relevance - (1 - lambda_param) * redundancy
            mmr_scores.append((score, idx))
            
        next_idx = max(mmr_scores, key=lambda x: x[0])[1]
        selected_indices.append(next_idx)
        remaining_indices.remove(next_idx)
        
    return selected_indices

# -------------------------------
# Multi-Stage Pipeline: Search -> Diversify -> Rerank
# -------------------------------
def retrieve_chunks(query: str, index, chunk_data, top_k: int = TOP_K_FINAL):
    query_vec = embed_query(query)
    
    # 1. Initial Semantic Retrieval (Fetch 30)
    _, indices = index.search(query_vec, TOP_K_RETRIVAL)
    candidates = [chunk_data[idx] for idx in indices[0]]
    candidate_embeddings = np.array([c["embedding"] for c in candidates])

    # 2. Apply MMR (Filter down to top 10 diverse candidates)
    diverse_indices = maximal_marginal_relevance(query_vec, candidate_embeddings, lambda_param=MMR_LAMBDA, k=10)
    diverse_candidates = [candidates[i] for i in diverse_indices]

    # 3. Cross-Encoder Rerank (Deep Accuracy check)
    pairs = [[query, res["text"]] for res in diverse_candidates]
    cross_scores = reranker.predict(pairs)

    for i, res in enumerate(diverse_candidates):
        res["rerank_score"] = float(cross_scores[i])

    sorted_results = sorted(diverse_candidates, key=lambda x: x["rerank_score"], reverse=True)

    # 4. Final Formatting
    return [{
        "rank": i + 1,
        "score": res["rerank_score"],
        "text": res["text"],
        "source": res["source"],
        "section": res["section"]
    } for i, res in enumerate(sorted_results[:top_k])]

