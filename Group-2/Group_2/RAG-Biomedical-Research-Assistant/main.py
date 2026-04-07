import os
from pathlib import Path

# -------------------------------
# Project modules
# -------------------------------
from query_parser import QueryParser
from document_retriever import BiomedicalDocumentRetriever
from pdf_cleaner import process_pdfs           # Step 3: PDF → cleaned chunks
# text_chunker import REMOVED — pdf_cleaner.py already chunks the text.
# Running text_chunker on top was double-chunking and causing KeyError: 'section'
from chunk_embedder import process_all as embed_chunks  # Step 4: chunks → embeddings

from faiss_searcher import load_chunks, build_faiss_index, retrieve_chunks
from flan_generator import RAGAnswerPipeline


from clinical_verify import clinical_verify

# =========================================================
# Configuration
# =========================================================
PDF_DIR         = "data/pdfs"
CLEANED_DIR     = "papers"          # pdf_cleaner.py writes here
EMBEDDINGS_FILE = "chunk_embeddings.json"
TOP_K           = 5


# =========================================================
# STEP 1–4: BUILD CORPUS
# (Step 4 is now embedding — chunking is done inside pdf_cleaner)
# =========================================================
def build_corpus(user_query: str, max_papers: int = 5):

    # --------------------------------------------------
    # STEP 1: Query Parsing
    # --------------------------------------------------
    print("\n" + "=" * 80)
    print("STEP 1: Query Parsing")
    print("=" * 80)

    qp     = QueryParser()
    parsed = qp.parse_structured_query(user_query)
    start_year, end_year = qp.parse_timeframe(parsed.get("timeframe", ""))

    search_text = " ".join([
        parsed.get("research_keyword", ""),
        parsed.get("intervention", ""),
        parsed.get("condition", "")
    ]).strip()

    if not search_text:
        raise RuntimeError("❌ Failed to construct Europe PMC query from parsed fields")

    print(f"Europe PMC query : {search_text}")
    print(f"Timeframe        : {start_year}–{end_year}")

    # --------------------------------------------------
    # STEP 2: Document Retrieval (Europe PMC)
    # --------------------------------------------------
    print("\n" + "=" * 80)
    print("STEP 2: Document Retrieval (Europe PMC)")
    print("=" * 80)

    retriever = BiomedicalDocumentRetriever(temp_dir=PDF_DIR)
    stats     = retriever.retrieve_documents(
        query=search_text,
        start_year=start_year,
        end_year=end_year,
        max_papers=max_papers,
        download_pdfs=True,
        save_abstracts=True
    )
    print("Retrieval stats:", stats["stats"])

    # --------------------------------------------------
    # STEP 3: PDF Cleaning, Section Extraction & Chunking
    # pdf_cleaner.py handles all three in one pass:
    #   PDF → markdown → section filtering → chunks → papers/*.json
    # --------------------------------------------------
    print("\n" + "=" * 80)
    print("STEP 3: PDF Cleaning, Section Extraction & Chunking")
    print("=" * 80)

    process_pdfs()

    cleaned = list(Path(CLEANED_DIR).glob("*.json"))
    if not cleaned:
        raise RuntimeError("❌ No cleaned papers found in papers/")

    print(f"✅ Cleaned & chunked documents: {len(cleaned)}")

    # --------------------------------------------------
    # STEP 4: Chunk Embedding
    # chunk_embedder.py reads from papers/ directly
    # --------------------------------------------------
    print("\n" + "=" * 80)
    print("STEP 4: Chunk Embedding")
    print("=" * 80)

    embed_chunks()

    if not Path(EMBEDDINGS_FILE).exists():
        raise RuntimeError("❌ Embedding file missing after embed step")

    print("✅ Embeddings ready")


# =========================================================
# STEP 5–8: RETRIEVAL → GENERATION → VERIFICATION
# =========================================================
def answer_question(user_query: str):

    # --------------------------------------------------
    # STEP 5: FAISS Index Construction
    # --------------------------------------------------
    print("\n" + "=" * 80)
    print("STEP 5: FAISS Index Construction")
    print("=" * 80)

    texts, vectors = load_chunks()
    index          = build_faiss_index(vectors)

    # --------------------------------------------------
    # STEP 6: Semantic Retrieval
    # --------------------------------------------------
    print("\n" + "=" * 80)
    print("STEP 6: Semantic Retrieval")
    print("=" * 80)

    retrieved = retrieve_chunks(
        query=user_query,
        index=index,
        chunk_data=texts,
        top_k=TOP_K
    )

    if not retrieved:
        raise RuntimeError("❌ No chunks retrieved for this query")
    '''
    
    print(f"\n{'Rank':<5} | {'Score':<8} | {'Section':<15} | Source")
    print("-" * 70)
    for r in retrieved:
        print(f"{r['rank']:<5} | {r['score']:<8.3f} | {r['section']:<15} | {r['source']}")
    '''
    
    print(retrieved)
       # --------------------------------------------------
    # STEP 7: Hybrid Extractive + Abstractive Generation
    # (SentenceExtractor → Mistral via Ollama)
    # --------------------------------------------------
    print("\n" + "=" * 80)
    print("STEP 7: Hybrid Extractive + Abstractive Generation")
    print("=" * 80)

    # Convert retrieved FAISS chunks into raw context strings
    contexts = [r["text"] for r in retrieved]

    # Initialize pipeline (only once ideally — kept here for minimal modification)
    pipeline = RAGAnswerPipeline(
        extractor_kwargs=dict(
            top_n=5,
            candidate_pool_size=20,
            mmr_lambda=0.7,
        ),
        generator_kwargs=dict(
            model="mistral",      # must match `ollama list`
            temperature=0.2,
            top_p=0.9,
            max_tokens=512,
        ),
        shared_device="cpu",     # change to "cuda" if using GPU
    )

    result = pipeline.run(
        query=user_query,
        contexts=contexts
    )

    final_answer = result.answer

    print("\n Extracted Evidence Sentences:")
    print("-" * 60)
    for s in result.extraction.selected:
        print(f"[Rank {s.rank}] {s.text}")

    print("\n Answer generated using hybrid RAG pipeline.")


    # --------------------------------------------------
    # STEP 8: Clinical Verification
    # clinical_verify receives the plain answer string
    # --------------------------------------------------
    print("\n" + "=" * 80)
    print("STEP 8: Clinical Verification")
    print("=" * 80)

    verification_report = clinical_verify(
        generated=final_answer,   # plain string — NOT the full dict
        chunks=retrieved,
        question=user_query,
        threshold=0.7
    )

    print("\nVERIFICATION REPORT:")
    print("-" * 60)
    print(f"Status           : {verification_report['status']}")
    print(f"Avg Similarity   : {verification_report['avg_similarity']}")
    print(f"Top Chunk Scores : {verification_report['top3_scores']}")
    print(f"Answer Relevancy : {verification_report['relevancy']}")
    print("-" * 60)

    return final_answer, verification_report


# =========================================================
# ENTRY POINT
# =========================================================
if __name__ == "__main__":

    print("\n" + "=" * 80)
    print("BIOMEDICAL RAG QUESTION ANSWERING SYSTEM")
    print("=" * 80)

    user_query = input("\nEnter biomedical research question:\n> ").strip()
    if not user_query:
        raise ValueError("❌ Query cannot be empty")

    build_corpus(user_query)

    final_answer, verification = answer_question(user_query)

    print("\n" + "=" * 80)
    print("FINAL ANSWER")
    print("=" * 80)
    print(final_answer)

    print("\n" + "=" * 80)
    print("FINAL VERIFICATION SUMMARY")
    print("=" * 80)
    print(f"Status           : {verification['status']}")
    print(f"Avg Similarity   : {verification['avg_similarity']}")
    print(f"Top Chunk Scores : {verification['top3_scores']}")
    print(f"Answer Relevancy : {verification['relevancy']}")