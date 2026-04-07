import os
import json
import requests
from pathlib import Path
from tqdm import tqdm
from xml.etree import ElementTree as ET


class BiomedicalDocumentRetriever:

    def __init__(self, temp_dir="data/pdfs"):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        self.europepmc_search_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

    # ==============================
    # NEW: Check API Status
    # ==============================
    def check_europepmc_status(self):
        try:
            response = requests.get(self.europepmc_search_url, timeout=5)
            if response.status_code == 200:
                return True
        except:
            pass
        return False

    # ==============================
    # PRIMARY: Europe PMC Search
    # ==============================
    def search_europepmc(self, query: str, start_year=None, end_year=None, max_results=10):

        # 🔴 Step 1: Check API health before using it
        if not self.check_europepmc_status():
            print("⚠ Europe PMC API is DOWN. Switching to PubMed fallback...")
            return self.search_pubmed_fallback(query, start_year, end_year, max_results)

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

        # 🔁 Retry logic (3 attempts)
        for attempt in range(3):
            try:
                r = requests.get(self.europepmc_search_url, params=params, timeout=15)
                r.raise_for_status()

                data = r.json()
                results = data.get("resultList", {}).get("result", [])

                if not results:
                    print("⚠ No results from Europe PMC. Falling back...")
                    return self.search_pubmed_fallback(query, start_year, end_year, max_results)

                return results

            except requests.exceptions.Timeout:
                print(f"⏳ Timeout (Attempt {attempt+1}/3)... retrying")

            except requests.exceptions.RequestException as e:
                print(f"✗ Europe PMC error: {e}")
                break

        # ❌ If all retries fail → fallback
        return self.search_pubmed_fallback(query, start_year, end_year, max_results)

    # ==============================
    # FALLBACK: PubMed Search
    # ==============================
    def search_pubmed_fallback(self, query, start_year=None, end_year=None, max_results=10):
        print("⚠ Using PubMed fallback...")

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

            r = requests.get(search_url, params=search_params, timeout=15)
            r.raise_for_status()
            id_list = r.json()["esearchresult"]["idlist"]

            if not id_list:
                return []

            # Step 2: Fetch details
            fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(id_list),
                "retmode": "xml"
            }

            r = requests.get(fetch_url, params=fetch_params, timeout=15)
            r.raise_for_status()

            root = ET.fromstring(r.content)
            results = []

            for article in root.findall(".//PubmedArticle"):
                title = article.findtext(".//ArticleTitle")
                abstract = article.findtext(".//AbstractText")
                year = article.findtext(".//PubDate/Year")

                results.append({
                    "title": title,
                    "abstractText": abstract,
                    "pubYear": year,
                    "authorString": "",
                    "journalTitle": "",
                    "pmcid": None,
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
        urls = entry.get("fullTextUrlList", {}).get("fullTextUrl", [])
        for u in urls:
            if u.get("documentStyle") == "pdf":
                return u.get("url")

        pmcid = entry.get("pmcid")
        if pmcid:
            return f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf"

        return None

    # ==============================
    # Download PDF
    # ==============================
    def download_pdf(self, title: str, url: str):
        safe_title = "".join(c if c.isalnum() else "_" for c in title)[:50]
        out_path = self.temp_dir / f"{safe_title}.pdf"

        try:
            r = requests.get(url, stream=True, timeout=60)

            if r.status_code == 200:
                content_length = int(r.headers.get("content-length", 0))

                # 🛑 Avoid downloading invalid PDFs
                if content_length < 1000:
                    return None

                with open(out_path, "wb") as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)

                return str(out_path)

        except Exception as e:
            print(f"✗ Error downloading PDF {title}: {e}")

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

        entries = self.search_europepmc(
            query, start_year, end_year, max_results=max_papers * 3
        )

        results = []
        downloaded_count = 0

        with tqdm(total=max_papers, desc="Downloading papers") as pbar:
            for entry in entries:
                if downloaded_count >= max_papers:
                    break

                title = entry.get("title", "paper")
                pdf_path = None
                abstract_path = None

                pdf_url = self.extract_pdf_link(entry)

                if download_pdfs and pdf_url:
                    pdf_path = self.download_pdf(title, pdf_url)
                else:
                    continue

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

        return {
            "documents": results,
            "stats": {
                "retrieved": len(results),
                "pdf_downloaded": sum(1 for r in results if r["pdf_path"]),
                "abstracts_saved": sum(1 for r in results if r["abstract_path"])
            }
        }