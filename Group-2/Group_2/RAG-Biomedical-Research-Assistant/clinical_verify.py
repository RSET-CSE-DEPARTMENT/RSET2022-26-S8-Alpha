import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel

def load_clinicalbert():
    """Load ClinicalBERT on-demand"""
    print(" Loading ClinicalBERT...")
    tokenizer = AutoTokenizer.from_pretrained("emilyalsentzer/Bio_ClinicalBERT")
    model = AutoModel.from_pretrained("emilyalsentzer/Bio_ClinicalBERT")
    model.eval()
    print(" ClinicalBERT ready!")
    return tokenizer, model

def clinical_verify(generated: str, chunks: list, question: str, threshold=0.7, lazy_load=True):
    """
    Medical verification + Answer Relevancy using ClinicalBERT cosine similarity ONLY
    """
    if lazy_load:
        tokenizer, model = load_clinicalbert()
    else:
        tokenizer = AutoTokenizer.from_pretrained("emilyalsentzer/Bio_ClinicalBERT")
        model = AutoModel.from_pretrained("emilyalsentzer/Bio_ClinicalBERT")
        model.eval()

    device = next(model.parameters()).device
    
    # 1. FAITHFULNESS: Answer vs Source Chunks (existing)
    all_scores = []
    gen_tokens = tokenizer(generated, return_tensors="pt", truncation=True, max_length=512).to(device)
    
    with torch.no_grad():
        gen_emb = model(**gen_tokens).last_hidden_state.mean(dim=1)
    
    for chunk in chunks[:3]:  # Top 3 only
        chunk_tokens = tokenizer(chunk["text"], return_tensors="pt", truncation=True, max_length=512).to(device)
        with torch.no_grad():
            chunk_emb = model(**chunk_tokens).last_hidden_state.mean(dim=1)
        
        sim = F.cosine_similarity(gen_emb, chunk_emb).item()
        all_scores.append(sim)
    
    avg_sim = sum(all_scores) / len(all_scores)
    status = "MEDICALLY GROUNDED" if avg_sim >= threshold else "NEEDS MORE EVIDENCE"
    
    # 2. ANSWER RELEVANCY: Question vs Answer (COSINE ONLY - NEW!)
    q_tokens = tokenizer(question, return_tensors="pt", truncation=True, max_length=512).to(device)
    with torch.no_grad():
        q_emb = model(**q_tokens).last_hidden_state.mean(dim=1)
    
    relevancy = F.cosine_similarity(q_emb, gen_emb).item()
    
    return {
        "status": status,
        "avg_similarity": round(avg_sim, 4),      # Faithfulness (Answer vs Chunks)
        "top3_scores": [round(s, 3) for s in all_scores],
        "chunks_used": 3,
        # NEW: Pure Cosine Relevancy
        "relevancy": round(relevancy, 4),         # Question vs Answer cosine
        "question_answer_sim": round(relevancy, 4)
    }
