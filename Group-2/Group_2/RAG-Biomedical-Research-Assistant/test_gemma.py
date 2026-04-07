import os
import json
import requests
from pathlib import Path
from tqdm import tqdm
from xml.etree import ElementTree as ET
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class BiomedicalDocumentRetriever:

    def __init__(self, temp_dir="data/pdfs"):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        self.europepmc_search_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
        
        # Create session with retry logic and proper headers
        self.session = self._create_session()

    def _create_session(self):
        """
        Create a requests session with retry logic and proper headers.
        """
        session = requests.Session()
        
        # Retry strategy: 3 retries with exponential backoff
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,  # Wait 1s, 2s, 4s between retries
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Add proper headers to avoid being blocked
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/html, application/pdf',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive'
        })
        
        return session

    # ==============================
    # PRIMARY: Europe PMC Search
    # ==============================
    def search_europepmc(self, query: str, start_year=None, end_year=None, max_results=10):
        q = query
        if start_year and end_year:
            q += f" AND PUB_YEAR:[{start_year} TO {end_year}] AND OPEN_ACCESS:Y"

        params = {
            "query": q,
            "format": "json",
            "pageSize": max_results,
            "resultType": "core",
            "synonym": "true"
        }

        try:
            r = self.session.get(self.europepmc_search_url, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            results = data.get("resultList", {}).get("result", [])

            if not results:
                print("⚠ No results from Europe PMC, trying PubMed...")
                return self.search_pubmed_fallback(query, start_year, end_year, max_results)

            print(f"✓ Found {len(results)} papers from Europe PMC")
            return results

        except Exception as e:
            print(f"✗ Europe PMC search error: {e}")
            return self.search_pubmed_fallback(query, start_year, end_year, max_results)

    # ==============================
    # FALLBACK: PubMed Search
    # ==============================
    def search_pubmed_fallback(self, query, start_year=None, end_year=None, max_results=10):
        print("⚠ Switching to PubMed fallback...")

        try:
            date_filter = ""
            if start_year and end_year:
                date_filter = f" AND ({start_year}:{end_year}[dp])"

            # Step 1: Search PubMed
            search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            search_params = {
                "db": "pubmed",
                "term": query + date_filter,
                "retmax": max_results,
                "retmode": "json"
            }

            r = self.session.get(search_url, params=search_params, timeout=30)
            r.raise_for_status()
            id_list = r.json()["esearchresult"]["idlist"]

            if not id_list:
                print("✗ No results from PubMed")
                return []

            print(f"✓ Found {len(id_list)} papers from PubMed")
            
            # Add delay to avoid rate limiting
            time.sleep(0.5)

            # Step 2: Fetch details
            fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(id_list),
                "retmode": "xml"
            }

            r = self.session.get(fetch_url, params=fetch_params, timeout=30)
            r.raise_for_status()

            root = ET.fromstring(r.content)
            results = []

            for article in root.findall(".//PubmedArticle"):
                title = article.findtext(".//ArticleTitle")
                abstract = article.findtext(".//AbstractText")
                year = article.findtext(".//PubDate/Year")
                pmid = article.findtext(".//PMID")

                results.append({
                    "title": title,
                    "abstractText": abstract,
                    "pubYear": year,
                    "authorString": "",
                    "journalTitle": "",
                    "pmcid": None,
                    "pmid": pmid,
                    "doi": None,
                    "fullTextUrlList": {}
                })

            return results

        except Exception as e:
            print(f"✗ PubMed fallback failed: {e}")
            return []

    # ==============================
    # Extract PDF Link
    # ==============================
    def extract_pdf_link(self, entry):
        """
        Try multiple PDF sources in priority order.
        """
        # Priority 1: Direct PDF URL from fullTextUrlList
        urls = entry.get("fullTextUrlList", {}).get("fullTextUrl", [])
        for u in urls:
            if u.get("documentStyle") == "pdf":
                return u.get("url")

        # Priority 2: Europe PMC PDF renderer
        pmcid = entry.get("pmcid")
        if pmcid:
            return f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf"
        
        # Priority 3: Try DOI-based resolution
        doi = entry.get("doi")
        if doi:
            # Unpaywall API for open access PDFs
            try:
                unpaywall_url = f"https://api.unpaywall.org/v2/{doi}?email=your_email@example.com"
                r = self.session.get(unpaywall_url, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("is_oa") and data.get("best_oa_location"):
                        pdf_url = data["best_oa_location"].get("url_for_pdf")
                        if pdf_url:
                            return pdf_url
            except:
                pass

        return None

    # ==============================
    # Download PDF with Retry Logic
    # ==============================
    def download_pdf(self, title: str, url: str, max_retries=3):
        """
        Download PDF with retry logic and proper error handling.
        """
        safe_title = "".join(c if c.isalnum() else "_" for c in title)[:50]
        out_path = self.temp_dir / f"{safe_title}.pdf"

        for attempt in range(max_retries):
            try:
                # Add delay between attempts
                if attempt > 0:
                    wait_time = 2 ** attempt  # Exponential backoff: 2s, 4s, 8s
                    print(f"   Retry {attempt + 1}/{max_retries} after {wait_time}s...")
                    time.sleep(wait_time)
                
                # Stream download with longer timeout
                r = self.session.get(url, stream=True, timeout=120)
                
                # Check if response is actually a PDF
                content_type = r.headers.get('content-type', '').lower()
                if 'pdf' not in content_type and 'octet-stream' not in content_type:
                    print(f"   ⚠ URL does not return PDF (got {content_type})")
                    return None
                
                if r.status_code == 200:
                    # Check content length
                    content_length = int(r.headers.get('content-length', 0))
                    if content_length > 0 and content_length < 1000:
                        print(f"   ⚠ PDF too small ({content_length} bytes), likely invalid")
                        continue
                    
                    # Write file
                    with open(out_path, "wb") as f:
                        for chunk in r.iter_content(8192):
                            if chunk:
                                f.write(chunk)
                    
                    # Verify file size
                    if out_path.stat().st_size > 1000:
                        print(f"   ✓ Downloaded {title[:50]}... ({out_path.stat().st_size} bytes)")
                        return str(out_path)
                    else:
                        print(f"   ⚠ Downloaded file too small, retrying...")
                        out_path.unlink()
                        
                elif r.status_code == 403:
                    print(f"   ✗ Access forbidden (403) - PDF not freely available")
                    return None
                elif r.status_code == 404:
                    print(f"   ✗ PDF not found (404)")
                    return None
                    
            except requests.exceptions.ConnectionError as e:
                print(f"   ✗ Connection error (attempt {attempt + 1}/{max_retries}): {e}")
            except requests.exceptions.Timeout as e:
                print(f"   ✗ Timeout (attempt {attempt + 1}/{max_retries}): {e}")
            except Exception as e:
                print(f"   ✗ Error downloading (attempt {attempt + 1}/{max_retries}): {e}")

        print(f"   ✗ Failed to download {title[:50]}... after {max_retries} attempts")
        return None

    # ==============================
    # Save Abstract
    # ==============================
    def save_abstract(self, entry, filename: str):
        abstract = entry.get("abstractText")
        if not abstract:
            return None

        safe_title = "".join(c if c.isalnum() else "_" for c in filename)[:50]
        out_path = self.temp_dir / f"{safe_title}.txt"

        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(f"Title: {entry.get('title')}\n")
                f.write(f"Authors: {entry.get('authorString')}\n")
                f.write(f"Year: {entry.get('pubYear')}\n")
                f.write(f"Journal: {entry.get('journalTitle')}\n\n")
                f.write(abstract)
            return str(out_path)

        except Exception as e:
            print(f"✗ Error saving abstract {filename}: {e}")

        return None

    # ==============================
    # Retrieve Documents
    # ==============================
    def retrieve_documents(self, query, start_year=None, end_year=None,
                           max_papers=5, download_pdfs=True, save_abstracts=True):

        print(f"\n🔎 Searching for: '{query}'")
        print(f"   Years: {start_year or 'any'} - {end_year or 'any'}")
        print(f"   Max papers: {max_papers}\n")

        entries = self.search_europepmc(
            query, start_year, end_year, max_results=max_papers * 3
        )

        if not entries:
            print("✗ No papers found. Try broadening your search.")
            return {
                "documents": [],
                "stats": {
                    "retrieved": 0,
                    "pdf_downloaded": 0,
                    "abstracts_saved": 0
                }
            }

        results = []
        downloaded_count = 0

        with tqdm(total=max_papers, desc="Processing papers", unit="paper") as pbar:
            for entry in entries:
                if downloaded_count >= max_papers:
                    break

                title = entry.get("title", "Untitled")
                pdf_path = None
                abstract_path = None

                # Skip if no PDF available
                pdf_url = self.extract_pdf_link(entry)
                if not pdf_url:
                    print(f"   ⏭ Skipping '{title[:50]}...' (no PDF available)")
                    continue

                # Download PDF
                if download_pdfs:
                    pdf_path = self.download_pdf(title, pdf_url)
                    if not pdf_path:
                        continue  # Skip if download failed
                    
                    # Rate limiting: wait between downloads
                    time.sleep(1)

                # Save abstract
                if save_abstracts:
                    abstract_path = self.save_abstract(entry, title)

                results.append({
                    "title": title,
                    "year": entry.get("pubYear"),
                    "authors": entry.get("authorString"),
                    "journal": entry.get("journalTitle"),
                    "pmcid": entry.get("pmcid"),
                    "doi": entry.get("doi"),
                    "pdf_path": pdf_path,
                    "abstract_path": abstract_path
                })

                if pdf_path:
                    downloaded_count += 1
                    pbar.update(1)

        print(f"\n✓ Successfully retrieved {downloaded_count} papers")

        return {
            "documents": results,
            "stats": {
                "retrieved": len(results),
                "pdf_downloaded": sum(1 for r in results if r["pdf_path"]),
                "abstracts_saved": sum(1 for r in results if r["abstract_path"])
            }
        }


# ==============================
# Testing
# ==============================
if __name__ == "__main__":
    retriever = BiomedicalDocumentRetriever()
    
    result = retriever.retrieve_documents(
        query="gliclazide diabetes",
        start_year=2020,
        end_year=2024,
        max_papers=3
    )
    
    print("\n" + "=" * 60)
    print("RETRIEVAL SUMMARY")
    print("=" * 60)
    print(f"Papers retrieved: {result['stats']['retrieved']}")
    print(f"PDFs downloaded: {result['stats']['pdf_downloaded']}")
    print(f"Abstracts saved: {result['stats']['abstracts_saved']}")
    print("\nRetrieved papers:")
    for doc in result["documents"]:
        print(f"  • {doc['title']}")
        print(f"    Year: {doc['year']} | PDF: {'✓' if doc['pdf_path'] else '✗'}")