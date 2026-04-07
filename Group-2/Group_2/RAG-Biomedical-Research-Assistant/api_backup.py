import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any

# Import your existing logic
from query_parser import QueryParser
from document_retriever import BiomedicalDocumentRetriever
from pdf_cleaner import process_pdfs
from text_chunker import process_all as process_text_chunks
from chunk_embedder import process_all as embed_chunks
from faiss_searcher import load_chunks, build_faiss_index, retrieve_chunks
from flan_generator import build_synthesis_prompt, generate_answer

app = FastAPI(title="Biomedical RAG Assistant")

# Step 1: Fix CORS (Crucial for React)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # Your React App URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request/response models
class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]

# Global variable to hold the index so we don't rebuild it on every request
faiss_index = None
texts = None

@app.on_event("startup")
async def startup_event():
    """Load FAISS index and texts once when the server starts."""
    global faiss_index, texts
    # Assuming you've already run build_corpus/build_embeddings once manually
    if os.path.exists("chunk_embeddings.json"):
        texts, vectors = load_chunks()
        faiss_index = build_faiss_index(vectors)
        print("✅ FAISS Index Loaded")

@app.post("/generate-answer", response_model=QueryResponse)
async def handle_rag_query(request: QueryRequest):
    try:
        user_query = request.query
        
        # 1. Retrieval (Semantic search using FAISS)
        retrieved = retrieve_chunks(
            query=user_query,
            index=faiss_index,
            texts=texts,
            top_k=5
        )
        
        if not retrieved:
            raise HTTPException(status_code=404, detail="No relevant context found")

        # 2. Extract context and synthesize answer
        # Using the improved prompt logic we discussed (Thematic/Pathway aware)
        evidence = [r["text"] for r in retrieved]
        prompt = build_synthesis_prompt(user_query, evidence)
        answer = generate_answer(prompt)
        
        # 3. Format response for React
        return {
            "answer": answer,
            "sources": retrieved # Includes 'text', 'score', 'rank'
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)