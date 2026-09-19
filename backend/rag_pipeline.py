from retriever import search_medical_research
from llm import generate_answer


# ============================================================
# CREATE CONTEXT
# ============================================================

def create_context(results):
    """
    Convert retrieved hybrid-search results
    into a context string for the LLM.
    """

    if not results:
        return "No relevant medical research was found."

    context_parts = []

    for rank, result in enumerate(results, start=1):

        document = result.get("document", "")
        metadata = result.get("metadata", {})

        page = metadata.get("page", "N/A")
        document_id = metadata.get(
            "document_id",
            "N/A"
        )
        source = metadata.get(
            "source",
            "N/A"
        )

        context_parts.append(
            f"""
[Research Result {rank}]
Source: {source}
Page: {page}

Content:
{document}
"""
        )

    return "\n".join(context_parts)


# ============================================================
# RUN RAG PIPELINE
# ============================================================

def run_rag(question: str,
            document_ids: list = None) -> dict:
    """
    Complete RAG pipeline:

    Question
        ↓
    Retriever
        ↓
    Relevant chunks
        ↓
    Context creation
        ↓
    LLM
        ↓
    Answer + Sources
    """

    # --------------------------------------------------------
    # 1. Retrieve relevant documents
    # --------------------------------------------------------

    print("\nSearching medical research...")

    results = search_medical_research(
        question,
        top_k=5,
        document_ids=document_ids
    )

    # --------------------------------------------------------
    # 2. Create context
    # --------------------------------------------------------

    context = create_context(results)

    # --------------------------------------------------------
    # 3. Generate answer
    # --------------------------------------------------------

    print("\nGenerating answer with Llama 3.2...")

    answer = generate_answer(
        question,
        context
    )

    # --------------------------------------------------------
    # 4. Extract sources
    #
    # IMPORTANT:
    # results is a LIST returned by retriever.py.
    # Each result contains:
    #
    # {
    #     "document": ...,
    #     "metadata": ...
    # }
    # --------------------------------------------------------

    sources = []

    for result in results:

        metadata = result.get(
            "metadata",
            {}
        )

        if metadata:

            sources.append({
                "source": metadata.get(
                    "source",
                    "Unknown"
                ),

                "page": metadata.get(
                    "page",
                    "Unknown"
                ),

                "document_id": metadata.get(
                    "document_id",
                    "Unknown"
                ),

                "chunk": metadata.get(
                    "chunk",
                    "Unknown"
                )
            })

    # --------------------------------------------------------
    # 5. Return final result
    # --------------------------------------------------------

    return {
        "answer": answer,
        "sources": sources
    }


# ============================================================
# TEST RAG DIRECTLY FROM TERMINAL
# ============================================================

if __name__ == "__main__":

    question = input(
        "\nEnter your medical research question: "
    ).strip()

    if not question:

        print("No question provided.")

    else:

        result = run_rag(question)

        print("\n================================")
        print("             ANSWER")
        print("================================")

        print(result["answer"])

        print("\n================================")
        print("             SOURCES")
        print("================================")

        if result["sources"]:

            for source in result["sources"]:

                print(
                    f"Source: {source['source']} | "
                    f"Page: {source['page']} | "
                    f"Chunk: {source['chunk']}"
                )

        else:

            print("No sources found.")