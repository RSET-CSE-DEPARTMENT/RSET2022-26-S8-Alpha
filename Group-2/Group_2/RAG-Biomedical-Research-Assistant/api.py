from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from cleanup import cleanup_temp_data
from main import build_corpus, answer_question

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str


@app.get("/")
def health():
    return {"status": "Biomedical RAG Backend Running"}


@app.post("/generate-answer")
def generate(req: QueryRequest):
    try:
        user_query = req.query.strip()

        if not user_query:
            return {
                "answer": "Query cannot be empty.",
                "sources": [],
                "verification": {}
            }

        print("\n" + "=" * 80)
        print("🚀 FULL PIPELINE TRIGGERED")
        print("=" * 80)

        # --------------------------------------------------
        # STEP 1–4: Build Corpus (Retrieval + Cleaning + Embedding)
        # --------------------------------------------------
        papers_metadata = build_corpus(user_query, max_papers=3)
        # build_corpus should return a list of dicts with paper metadata.
        # Expected shape per paper:
        # {
        #   "title": str,
        #   "authors": str,       # e.g. "Smith J, Doe A, et al."
        #   "year": int | str,
        #   "doi": str,           # e.g. "10.1056/NEJMoa..."
        #   "journal": str,       # e.g. "N Engl J Med"
        #   "abstract": str,      # optional — used for snippet
        #   "url": str,           # optional — fallback link
        # }
        # If build_corpus doesn't return metadata yet, patch it to do so
        # (see note below). For now we gracefully handle None / empty list.
        if not papers_metadata:
            papers_metadata = []

        # --------------------------------------------------
        # STEP 5–8: Retrieval → Generation → Verification
        # --------------------------------------------------
        from query_parser import QueryParser

        qp = QueryParser()
        parsed = qp.parse_structured_query(user_query)

        clean_query = " ".join(filter(None, [
            parsed.get("research_keyword", ""),
            parsed.get("intervention", ""),
            parsed.get("condition", "")
        ])).strip()

        if not clean_query:
            clean_query = user_query

        answer, verification_report = answer_question(clean_query)

        # --------------------------------------------------
        # Build structured sources list for the frontend
        # --------------------------------------------------
        sources = []
        for paper in papers_metadata:
            doi = paper.get("doi", "")
            sources.append({
                "title":   paper.get("title", "Untitled"),
                "authors": paper.get("authors", ""),
                "year":    paper.get("year", ""),
                "doi":     doi,
                "journal": paper.get("journal", ""),
                "abstract": paper.get("abstract", ""),
                # Resolve a clickable URL: prefer DOI link, fallback to url field
                "url": f"https://doi.org/{doi}" if doi else paper.get("url", ""),
            })

        return {
            "answer": answer,
            "sources": sources,
            "verification": verification_report
        }

    except Exception as e:
        print("🚨 Backend Error:", e)
        return {
            "answer": f"Backend Error: {str(e)}",
            "sources": [],
            "verification": {}
        }

    # finally:
    #     release_file_handles()
    #     cleanup_temp_data()