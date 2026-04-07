import json
from pathlib import Path

def audit_cleaned_data(papers_dir="papers"):
    print("📋 STARTING PDF CLEANER AUDIT...")
    cleaned_files = list(Path(papers_dir).glob("*.json"))
    
    if not cleaned_files:
        print("❌ No processed JSON files found in 'papers/' folder.")
        return

    # Sections we expect to be GONE
    forbidden = ["ABSTRACT", "INTRODUCTION", "REFERENCES", "BIBLIOGRAPHY"]
    total_violations = 0
    
    for jf in cleaned_files:
        with open(jf, "r", encoding="utf-8") as f:
            data = json.load(f)
            chunks = data.get("chunks", [])
            
            # Extract unique section names found in this file
            sections_found = set(c.get("section", "UNKNOWN") for c in chunks)
            
            # Check for violations
            violations = [s for s in sections_found if s in forbidden]
            
            if violations:
                print(f"⚠️  FAIL: {jf.name} contains forbidden sections: {violations}")
                total_violations += len(violations)
            else:
                print(f"✅ PASS: {jf.name} is clean. (Sections: {list(sections_found)})")

    print("\n" + "="*40)
    if total_violations == 0:
        print("🎉 AUDIT SUCCESS: All citations and abstracts removed.")
    else:
        print(f"❌ AUDIT FAILED: Found {total_violations} instances of noise sections.")
    print("="*40)

if __name__ == "__main__":
    audit_cleaned_data()