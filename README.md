# 🧠 MediResearch AI

### AI-Powered Medical Research Assistant using RAG

MediResearch AI is an AI-powered research assistant designed to help users explore and understand medical research papers more efficiently.

Users can upload medical research PDFs and ask questions about their contents. Instead of relying only on the general knowledge of an LLM, MediResearch AI retrieves relevant information from the uploaded documents and uses that evidence to generate grounded answers.

The system also provides source references, allowing users to trace an answer back to the relevant document, page, and retrieved section.

> ⚠️ **Disclaimer:** MediResearch AI is designed for research and educational purposes. It is not intended to provide medical diagnosis, treatment decisions, or professional medical advice.

---

## 🚀 What Problem Does It Solve?

Medical research papers can contain dozens or hundreds of pages, making it time-consuming to locate specific information.

For example, a researcher may upload a paper and ask:

> **"What are the major causes of cancer mentioned in this paper?"**

Instead of manually searching through the entire document, MediResearch AI:

1. Processes the uploaded research paper
2. Extracts and cleans the text
3. Divides the document into meaningful chunks
4. Converts those chunks into semantic embeddings
5. Stores the embeddings in ChromaDB
6. Searches for the most relevant research passages
7. Provides the retrieved context to the LLM
8. Generates a concise answer
9. Displays the sources used to generate the answer

This creates a **document-grounded research workflow** rather than a generic chatbot.

---

# 🔍 How MediResearch AI Works

```text
                    USER
                     │
                     ▼
              Upload Research PDF
                     │
                     ▼
             PDF Text Extraction
                     │
                     ▼
               Text Cleaning
                     │
                     ▼
             Intelligent Chunking
                     │
                     ▼
        Sentence Transformer Model
             (384-D Embeddings)
                     │
                     ▼
                 ChromaDB
              Vector Storage
                     │
                     ▼
              User Question
                     │
                     ▼
           Hybrid Retrieval
        ┌────────────┼────────────┐
        ▼            ▼            ▼
     Semantic      Keyword      Phrase
     Search        Matching     Matching
        └────────────┼────────────┘
                     ▼
             Relevant Context
                     │
                     ▼
              Llama 3.2
               via Ollama
                     │
                     ▼
              Grounded Answer
                     │
              ┌──────┴──────┐
              ▼             ▼
           Answer         Sources
