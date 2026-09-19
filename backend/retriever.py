import re
from pathlib import Path

import chromadb

from embeddings import _get_model


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = str(BASE_DIR / "data" / "chroma_db")

COLLECTION_NAME = "medical_research"

# Minimum score required for a result to be considered relevant
RELEVANCE_THRESHOLD = 0.25


# ============================================================
# STOP WORDS
# ============================================================

STOP_WORDS = {
    "what",
    "which",
    "who",
    "where",
    "when",
    "why",
    "how",
    "does",
    "do",
    "did",
    "is",
    "are",
    "was",
    "were",
    "the",
    "a",
    "an",
    "and",
    "or",
    "of",
    "in",
    "on",
    "for",
    "to",
    "with",
    "about",
    "research",
    "study",
    "discusses",
    "discuss",
    "related",
    "regarding",
}


# ============================================================
# TEXT TOKENIZATION
# ============================================================

def tokenize(text: str):
    """
    Convert text into useful lowercase tokens.
    """

    words = re.findall(
        r"\b[a-zA-Z0-9]+\b",
        text.lower()
    )

    return [
        word
        for word in words
        if word not in STOP_WORDS
    ]


# ============================================================
# KEYWORD SCORE
# ============================================================

def keyword_score(query: str, document: str):
    """
    Calculate the percentage of important query words
    that appear in the document.
    """

    query_words = set(tokenize(query))

    document_words = set(tokenize(document))

    if not query_words:
        return 0.0

    matched_words = query_words.intersection(
        document_words
    )

    return len(matched_words) / len(query_words)


# ============================================================
# PHRASE SCORE
# ============================================================

def phrase_score(query: str, document: str):
    """
    Give additional score when consecutive query words
    occur together in the document.
    """

    query_words = tokenize(query)

    document_text = document.lower()

    if len(query_words) < 2:
        return 0.0

    matched_phrases = 0

    for i in range(len(query_words) - 1):

        phrase = (
            query_words[i]
            + " "
            + query_words[i + 1]
        )

        if phrase in document_text:
            matched_phrases += 1

    max_score = len(query_words) - 1

    return matched_phrases / max_score


# ============================================================
# HYBRID SEARCH
# ============================================================

def search_medical_research(
    query: str,
    top_k: int = 5,
    document_ids: list = None
):
    """
    Search the medical research database.

    Hybrid ranking:

        Semantic similarity = 50%
        Keyword matching    = 35%
        Phrase matching     = 15%

    If document_ids is provided, only search chunks
    belonging to those documents.
    """

    if not query or not query.strip():
        return []

    query = query.strip()

    # --------------------------------------------------------
    # Create query embedding
    # --------------------------------------------------------

    query_embedding = _get_model().encode(
        query
    ).tolist()

    # --------------------------------------------------------
    # Connect to ChromaDB
    # --------------------------------------------------------

    client = chromadb.PersistentClient(
        path=DB_PATH
    )

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME
    )

    total_documents = collection.count()

    if total_documents == 0:
        return []

    # --------------------------------------------------------
    # Retrieve candidates
    #
    # If document_ids is provided, filter to only those
    # documents. Otherwise search all.
    # --------------------------------------------------------

    where_filter = None

    if document_ids:
        if len(document_ids) == 1:
            where_filter = {
                "document_id": document_ids[0]
            }
        else:
            where_filter = {
                "document_id": {
                    "$in": document_ids
                }
            }

    n_results = min(total_documents, 100)

    query_kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": [
            "documents",
            "metadatas",
            "distances"
        ],
    }

    if where_filter:
        query_kwargs["where"] = where_filter

    results = collection.query(**query_kwargs)

    documents = results.get(
        "documents",
        [[]]
    )[0]

    metadatas = results.get(
        "metadatas",
        [[]]
    )[0]

    distances = results.get(
        "distances",
        [[]]
    )[0]

    # --------------------------------------------------------
    # Calculate hybrid scores
    # --------------------------------------------------------

    ranked_results = []

    for doc, meta, distance in zip(
        documents,
        metadatas,
        distances
    ):

        # ----------------------------------------------------
        # Convert ChromaDB cosine distance
        # into a similarity score.
        #
        # Lower distance = more similar.
        # ----------------------------------------------------

        semantic_score = max(
            0.0,
            1.0 - (distance / 2.0)
        )

        # ----------------------------------------------------
        # Keyword score
        # ----------------------------------------------------

        keyword = keyword_score(
            query,
            doc
        )

        # ----------------------------------------------------
        # Phrase score
        # ----------------------------------------------------

        phrase = phrase_score(
            query,
            doc
        )

        # ----------------------------------------------------
        # Hybrid score
        # ----------------------------------------------------

        final_score = (
            (semantic_score * 0.50)
            +
            (keyword * 0.35)
            +
            (phrase * 0.15)
        )

        ranked_results.append({
            "document": doc,
            "metadata": meta,
            "distance": distance,
            "semantic_score": semantic_score,
            "keyword_score": keyword,
            "phrase_score": phrase,
            "final_score": final_score,
        })

    # --------------------------------------------------------
    # Sort highest score first
    # --------------------------------------------------------

    ranked_results.sort(
        key=lambda x: x["final_score"],
        reverse=True
    )

    # --------------------------------------------------------
    # Remove very weak results
    # --------------------------------------------------------

    relevant_results = [
        result
        for result in ranked_results
        if result["final_score"] >= RELEVANCE_THRESHOLD
    ]

    # --------------------------------------------------------
    # Return only requested number of results
    # --------------------------------------------------------

    return relevant_results[:top_k]


# ============================================================
# TERMINAL TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("          MEDIRESEARCH AI - RETRIEVER")
    print("=" * 60)

    question = input(
        "\nEnter your medical research question: "
    ).strip()

    if not question:

        print("\nNo query provided. Exiting...")

    else:

        print("\nSearching medical research...")

        results = search_medical_research(
            question,
            top_k=3
        )

        print()
        print("=" * 60)
        print("                  SEARCH RESULTS")
        print("=" * 60)

        # ----------------------------------------------------
        # No sufficiently relevant results
        # ----------------------------------------------------

        if not results:

            print()
            print(
                "No sufficiently relevant research "
                "was found."
            )

        # ----------------------------------------------------
        # Display results
        # ----------------------------------------------------

        else:

            for rank, result in enumerate(
                results,
                start=1
            ):

                doc = result["document"]
                meta = result["metadata"]

                relevance = (
                    result["final_score"] * 100
                )

                print()
                print(f"[Rank {rank}]")
                print(
                    f"Relevance: {relevance:.1f}%"
                )

                print(
                    f"Document: "
                    f"{meta.get('document_id', 'N/A')}"
                )

                print(
                    f"Page: "
                    f"{meta.get('page', 'N/A')}"
                )

                print(
                    f"Chunk: "
                    f"{meta.get('chunk', 'N/A')}"
                )

                print(
                    f"Source: "
                    f"{meta.get('source', 'N/A')}"
                )

                print()
                print("Content:")
                print(doc.strip())

                print("-" * 60)

        print()
        print("=" * 60)