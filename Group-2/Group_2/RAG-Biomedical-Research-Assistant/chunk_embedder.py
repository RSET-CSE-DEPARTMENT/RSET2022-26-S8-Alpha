import os
import json
from pathlib import Path
from typing import List, Dict
from nomic import embed, login

# -------------------------------
# Configuration
# -------------------------------
# Reads directly from pdf_cleaner.py output — text_chunker.py not needed
CHUNKS_DIR  = Path("papers")
OUTPUT_FILE = Path("chunk_embeddings.json")

EMBED_MODEL = "nomic-embed-text-v1"
BATCH_SIZE  = 32

# -------------------------------
# Nomic login
# -------------------------------
#NOMIC_API_KEY = os.environ.get("NOMIC_API_KEY", "nk-GWQDehM359GX9aHm0o6-mB2_uDEdu2Y-LZMQgdOJ3gs")
NOMIC_API_KEY = os.environ.get("NOMIC_API_KEY", "nk-OJ9AEZTjD05CvxwW8f1iKynFdZySGrDHbYINcO6nj1E")
login(NOMIC_API_KEY)

# -------------------------------
# Helper: Prep text for embedding
# -------------------------------
def prepare_text_for_embedding(chunk: Dict, source_title: str) -> str:
    # FIX: key is now "section" — matches pdf_cleaner.py output
    section = chunk.get("section", "General")
    text    = chunk.get("text", "")
    return f"Paper: {source_title} | Section: {section} | Content: {text}"

# -------------------------------
# Embed in batches
# -------------------------------
def embed_texts(texts: List[str]) -> List[List[float]]:
    embeddings = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        print(f"    Embedding batch {i // BATCH_SIZE + 1} "
              f"({len(batch)} texts)...")

        response = embed.text(
            texts=batch,
            model=EMBED_MODEL,
            task_type="search_document"
        )
        embeddings.extend(response["embeddings"])

    return embeddings

# -------------------------------
# Main pipeline
# -------------------------------
def process_all():
    json_files = list(CHUNKS_DIR.glob("*.json"))

    if not json_files:
        print(f"❌ No chunk JSON files found in {CHUNKS_DIR}")
        return

    all_records = []

    for jf in json_files:
        print(f"\n📄 Processing {jf.name}")

        try:
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"   ❌ Failed to read {jf.name}: {e}")
            continue

        chunks = data.get("chunks", [])
        source = data.get("source", jf.stem)

        if not chunks:
            print(f"   ⚠️  No chunks found in {jf.name} — skipping")
            continue

        texts_to_embed = [prepare_text_for_embedding(c, source) for c in chunks]
        embeddings     = embed_texts(texts_to_embed)

        enriched_chunks = []
        for chunk, emb in zip(chunks, embeddings):
            enriched_chunks.append({
                "chunk_id":  chunk.get("chunk_id"),
                "source":    source,
                # FIX: "section" key — consistent across all pipeline stages
                "section":   chunk.get("section", "General"),
                "text":      chunk.get("text", ""),
                "embedding": emb,
                "length":    chunk.get("length", len(chunk.get("text", "")))
            })

        all_records.append({
            "source":     source,
            "num_chunks": len(enriched_chunks),
            "chunks":     enriched_chunks
        })

        print(f"    {len(enriched_chunks)} chunks embedded from {jf.name}")

    # Save all embeddings
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_records, f, indent=2)

    total = sum(r["num_chunks"] for r in all_records)
    print(f"\n🎉 Done — {total} total chunks embedded → {OUTPUT_FILE}")


if __name__ == "__main__":
    process_all()