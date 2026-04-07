from query_parser import QueryParser
from document_retriever import BiomedicalDocumentRetriever

def main():
    # -------------------------------
    # 1. Input test query
    # -------------------------------
    query = "What is the symptoms of Parkinson's disease published in 2018-2023?"

    print("Original Query:")
    print(query)
    print("-" * 60)

    # -------------------------------
    # 2. Parse structured query
    # -------------------------------
    parser = QueryParser()
    parsed_query = parser.parse_structured_query(query)

    print("Parsed Query Components:")
    for k, v in parsed_query.items():
        print(f"{k}: {v}")
    print("-" * 60)

    # -------------------------------
    # 3. Parse timeframe
    # -------------------------------
    start_year, end_year = parser.parse_timeframe(parsed_query["timeframe"])

    print(f"Timeframe Parsed: {start_year} to {end_year}")
    print("-" * 60)

    # -------------------------------
    # 4. Build Europe PMC search query
    # -------------------------------
    search_query = (
        f"{parsed_query['intervention']} "
        f"{parsed_query['condition']}"
    ).strip()

    print("🔎 Europe PMC Search Query:")
    print(search_query)
    print("-" * 60)

    # -------------------------------
    # 5. Retrieve documents
    # -------------------------------
    retriever = BiomedicalDocumentRetriever(temp_dir="data/test_pdfs")

    results = retriever.retrieve_documents(
        query=search_query,
        start_year=start_year,
        end_year=end_year,
        max_papers=3,          # keep small for testing
        download_pdfs=True,
        save_abstracts=True
    )

    # -------------------------------
    # 6. Display results
    # -------------------------------
    print("\n Retrieved Documents:")
    for idx, doc in enumerate(results["documents"], start=1):
        print(f"\nPaper {idx}:")
        print(f"Title   : {doc['title']}")
        print(f"Year    : {doc['year']}")
        print(f"Journal : {doc['journal']}")
        print(f"PDF     : {doc['pdf_path']}")
        print(f"Abstract: {doc['abstract_path']}")

    print("\n Retrieval Stats:")
    for k, v in results["stats"].items():
        print(f"{k}: {v}")

    print("\n Test completed successfully!")

if __name__ == "__main__":
    main()
