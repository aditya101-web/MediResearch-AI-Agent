    # MediResearch-AI

AI-powered medical research assistant that uses Retrieval-Augmented Generation (RAG) to answer questions from uploaded medical research PDFs.

## Overview

MediResearch-AI allows users to upload medical research papers and ask questions about their content.

The system extracts text from PDFs, splits the content into meaningful chunks, converts the chunks into vector embeddings, stores them in ChromaDB, retrieves relevant research passages, and uses an LLM to generate answers with source and page citations.

> This project is designed for medical research and literature exploration. It is not intended for medical diagnosis or treatment decisions.

## Architecture

PDF Upload
→ PDF Text Extraction
→ Text Cleaning
→ Chunking
→ Sentence Transformer Embeddings
→ ChromaDB
→ Hybrid Retrieval
→ LLM
→ Answer + Sources

## Features

- Upload and process medical research PDFs
- PDF text extraction using pypdf
- Text cleaning and chunking
- Semantic embeddings using Sentence Transformers
- Persistent vector storage with ChromaDB
- Hybrid retrieval using semantic, keyword, and phrase matching
- AI-generated answers using Ollama
- Source and page-level citations
- FastAPI backend
- Web-based frontend
- Persistent conversation/document data

## Tech Stack

- Python
- FastAPI
- ChromaDB
- Sentence Transformers
- pypdf
- Ollama
- SQLite
- HTML
- CSS
- JavaScript

## Project Structure

```text
MediResearch-AI/
│
├── backend/
│   ├── api.py
│   ├── chunker.py
│   ├── database.py
│   ├── document_processor.py
│   ├── embeddings.py
│   ├── llm.py
│   ├── pdf_processor.py
│   ├── rag_pipeline.py
│   ├── retriever.py
│   ├── text_processor.py
│   └── vector_store.py
│
├── frontend/
│   ├── assets/
│   ├── css/
│   ├── js/
│   └── index.html
│
├── requirements.txt
├── .gitignore
└── README.md