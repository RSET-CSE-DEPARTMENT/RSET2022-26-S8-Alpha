import json
import re
from pathlib import Path
from typing import List, Dict

# -------------------------------
# Configuration
# -------------------------------
INPUT_DIR  = Path("papers")         # JSON files from pdf_cleaner.py
OUTPUT_DIR = Path("papers_chunks")  # Final chunks for embedding
MAX_CHARS  = 800                    # Safe embedding size
MIN_CHARS  = 200                    # Drop tiny noisy chunks

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------
# Load structured JSON
# -------------------------------
def load_json(json_path: Path) -> Dict:
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

# -------------------------------
# Sentence splitting (lightweight)
# -------------------------------
def split_sentences(text: str) -> List[str]:
    return re.split(r"(?<=[.!?])\s+", text)

# -------------------------------
# Re-chunk safely
# -------------------------------
def rechunk_text(text: str, max_chars: int) -> List[str]:
    sentences = split_sentences(text)
    chunks    = []
    buffer    = ""

    for s in sentences:
        if len(buffer) + len(s) <= max_chars:
            buffer += " " + s
        else:
            if buffer.strip():
                chunks.append(buffer.strip())
            buffer = s

    if buffer.strip():
        chunks.append(buffer.strip())

    return chunks

# -------------------------------
# Process a single JSON file
# -------------------------------
def process_file(json_path: Path):
    data         = load_json(json_path)
    final_chunks = []
    new_chunk_id = 0

    # FIX 1: Use .get() for top-level source — some PDFs may not have it
    doc_source = data.get("source", json_path.stem)

    for chunk in data.get("chunks", []):

        # FIX 2: Skip chunks with no text key entirely
        if "text" not in chunk:
            print(f"  [WARN] Chunk missing 'text' key in {json_path.name} — skipped")
            continue

        text = chunk["text"].strip()

        if len(text) < MIN_CHARS:
            continue

        # FIX 3: Use .get() for section — falls back to "General" if
        # pdf_cleaner.py didn't detect a section header for this chunk.
        # This was the direct cause of the KeyError: 'section' crash.
        section = chunk.get("section", "General")

        sub_chunks = (
            rechunk_text(text, MAX_CHARS)
            if len(text) > MAX_CHARS
            else [text]
        )

        for sub in sub_chunks:
            if len(sub) < MIN_CHARS:
                continue

            final_chunks.append({
                "chunk_id": new_chunk_id,
                "source":   doc_source,
                "section":  section,
                "text":     sub,
                "length":   len(sub)
            })
            new_chunk_id += 1

    out_file = OUTPUT_DIR / json_path.name

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "source":     doc_source,
                "num_chunks": len(final_chunks),
                "chunks":     final_chunks
            },
            f,
            indent=2,
            ensure_ascii=False
        )

    print(f"[SUCCESS] {json_path.name} → {len(final_chunks)} chunks")

# -------------------------------
# Main pipeline
# -------------------------------
def process_all():
    json_files = list(INPUT_DIR.glob("*.json"))

    if not json_files:
        print(f"[WARN] No JSON files found in {INPUT_DIR}")
        return

    for jf in json_files:
        print(f"[INFO] Processing {jf.name}")
        try:
            process_file(jf)
        except Exception as e:
            # FIX 4: Don't let one bad file crash the entire pipeline
            print(f"  [ERROR] Failed to process {jf.name}: {e}")
        print("-" * 50)

# -------------------------------
# Entry point
# -------------------------------
if __name__ == "__main__":
    process_all()