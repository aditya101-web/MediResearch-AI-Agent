import ollama


MODEL_NAME = "llama3.2"


def generate_answer(question, context):
    """
    Generate an answer using Ollama based only
    on the retrieved research context.
    """

    prompt = f"""
You are MediResearch AI, a medical research assistant.

Your job is to answer the user's question using ONLY the
provided research context.

IMPORTANT RULES:
1. Use only information present in the research context.
2. Do not invent or assume medical facts.
3. If the answer is not clearly present in the context, say:
   "The requested information was not found in the provided research."
4. Do not provide medical advice, diagnosis, or treatment recommendations.
5. Answer clearly and concisely.
6. Do not mention chunk numbers, chunk IDs, content numbers, embeddings,
   ChromaDB, vector databases, or internal retrieval details.
7. Do not say things like "according to chunk 2" or "content 2".
8. Do not create or guess page numbers. Page information will be handled
   separately by the application.
9. Summarize the relevant research information in natural language.
10. If the context contains conflicting information, clearly mention the
    conflict instead of choosing one without evidence.

RESEARCH CONTEXT:
{context}

USER QUESTION:
{question}

ANSWER:
"""

    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"]