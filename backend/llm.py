import os
from google import genai

MODEL_NAME = "gemini-2.5-flash"

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


def generate_answer(question, context):
    prompt = f"""
You are MediResearch AI, a medical research assistant.

Answer the user's question using ONLY the research context provided below.

Rules:
- Use only information present in the research context.
- Do not invent or assume facts.
- If the answer is not present in the context, say:
  "The requested information was not found in the provided research."
- Do not provide medical diagnosis or personalized treatment advice.
- If the research contains conflicting information, mention the conflict.
- Answer clearly and concisely.
- Do not mention embeddings, ChromaDB, vector databases, chunk IDs, or internal implementation details.
- Do not guess page numbers or sources.

RESEARCH CONTEXT:
{context}

USER QUESTION:
{question}

ANSWER:
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return response.text