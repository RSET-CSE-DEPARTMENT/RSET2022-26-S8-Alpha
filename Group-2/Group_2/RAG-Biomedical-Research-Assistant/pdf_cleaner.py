import pymupdf4llm
import re
import json
from pathlib import Path

# -------------------------------
# Configuration
# -------------------------------
PDF_DIR             = "data/pdfs"
OUTPUT_DIR          = "papers"
MAX_CHARS_PER_CHUNK = 1500
CHUNK_OVERLAP       = 200

# Sections to EXCLUDE completely
EXCLUDE_SECTIONS = {"ABSTRACT", "REFERENCES", "BIBLIOGRAPHY", "ACKNOWLEDGEMENTS"}

# Section header patterns
SECTION_PATTERNS = {
    "ABSTRACT":         r"(?i)^\s*(abstract|summary)\b",
    "INTRODUCTION":     r"(?i)^\s*(introduction|background)\b",
    "METHODS":          r"(?i)^\s*(methods|methodology|materials and methods|experimental procedures)\b",
    "RESULTS":          r"(?i)^\s*(results|findings)\b",
    "DISCUSSION":       r"(?i)^\s*(discussion)\b",
    "CONCLUSION":       r"(?i)^\s*(conclusion|conclusions)\b",
    "REFERENCES":       r"(?i)^\s*(references|bibliography|literature cited)\b",
    "ACKNOWLEDGEMENTS": r"(?i)^\s*(acknowledgements|acknowledgments|funding)\b",
}

Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)


def identify_section(header_text: str) -> str:
    """Map a header string to a known section type, or 'General'."""
    for section_key, pattern in SECTION_PATTERNS.items():
        if re.search(pattern, header_text, re.IGNORECASE):
            return section_key
    # FIX: Return "General" instead of "OTHER" so downstream
    # components have a consistent, meaningful fallback value.
    return "General"


def extract_sections_from_markdown(md_text: str) -> list:
    """Parse markdown into a list of {header, content} dicts."""
    sections      = []
    lines         = md_text.split('\n')
    current_header  = "General"
    current_content = []

    for line in lines:
        header_match = re.match(r'^(#{1,3})\s+(.+)$', line.strip())
        bold_match   = re.match(r'^\*\*(.+?)\*\*$', line.strip())

        if header_match or bold_match:
            # Save accumulated content under the previous header
            if current_content:
                content = '\n'.join(current_content).strip()
                if content:
                    sections.append({
                        'header':  current_header,
                        'content': content
                    })
            # Start a new section
            current_header  = (header_match.group(2) if header_match
                               else bold_match.group(1)).strip()
            current_content = []
        else:
            current_content.append(line)

    # Flush the final section
    if current_content:
        content = '\n'.join(current_content).strip()
        if content:
            sections.append({'header': current_header, 'content': content})

    return sections


def clean_content(content: str) -> str:
    """Remove noise: strikethrough, excess newlines, isolated page numbers."""
    content = re.sub(r'~~.*?~~', '', content)
    content = re.sub(r'\n{3,}', '\n\n', content)
    lines   = content.split('\n')
    lines   = [l for l in lines if not re.match(r'^\s*\d+\s*$', l)]
    return '\n'.join(lines).strip()


def process_pdfs():
    pdfs = list(Path(PDF_DIR).glob("*.pdf"))

    if not pdfs:
        print(f"[WARN] No PDFs found in {PDF_DIR}")
        return

    for pdf in pdfs:
        print(f"\n Processing: {pdf.name}")

        try:
            md_text = pymupdf4llm.to_markdown(str(pdf))
        except Exception as e:
            print(f"    Failed to extract markdown: {e}")
            continue

        # Basic markdown cleaning
        md_text = re.sub(r"DOI: https?://\S+", "", md_text)
        md_text = re.sub(r"\[\d+(?:,\s*\d+)*\]", "", md_text)

        sections = extract_sections_from_markdown(md_text)
        print(f"    Found {len(sections)} total sections")

        # Filter excluded sections
        keep_sections  = []
        excluded_count = 0

        for section in sections:
            # FIX: identify_section now returns "General" for unknowns,
            # so we map the header to its type just for filtering.
            section_type = identify_section(section['header'])

            if section_type in EXCLUDE_SECTIONS:
                print(f"    Excluding: {section_type} — '{section['header'][:40]}'")
                excluded_count += 1
            else:
                # Store the canonical section type on the section dict
                # so downstream tools can use it for filtering/ranking.
                section['section_type'] = section_type
                print(f"    Keeping:   {section_type} — '{section['header'][:40]}'")
                keep_sections.append(section)

        print(f"    Keeping {len(keep_sections)}, excluding {excluded_count}")

        # Chunk kept sections
        structured_chunks = []
        chunk_id          = 0

        for section in keep_sections:
            clean_text = clean_content(section['content'])

            if not clean_text or len(clean_text) < 100:
                continue

            start = 0
            while start < len(clean_text):
                end   = start + MAX_CHARS_PER_CHUNK
                chunk = clean_text[start:end]

                structured_chunks.append({
                    "chunk_id": chunk_id,
                    "source":   pdf.name,
                    # FIX: key is now "section" (not "section_header")
                    # so text_chunker.py and chunk_embedder.py both
                    # read it without a KeyError.
                    "section":  section['section_type'],
                    "text":     chunk,
                    "length":   len(chunk)
                })

                chunk_id += 1
                start    += (MAX_CHARS_PER_CHUNK - CHUNK_OVERLAP)

        # Save output
        if structured_chunks:
            out_file = Path(OUTPUT_DIR) / f"{pdf.stem}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump({
                    "source":            pdf.name,
                    "num_chunks":        len(structured_chunks),
                    "sections_kept":     len(keep_sections),
                    "sections_excluded": excluded_count,
                    "chunks":            structured_chunks
                }, f, indent=2, ensure_ascii=False)
            print(f"    Saved {len(structured_chunks)} chunks → {out_file}")
        else:
            print(f"     No content extracted from {pdf.name}")


if __name__ == "__main__":
    process_pdfs()