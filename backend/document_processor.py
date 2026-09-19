import hashlib
import re
from pathlib import Path

import chromadb
from pypdf import PdfReader

from pdf_processor import clean_text
from embeddings import create_embeddings
from database import (
    update_document_status,
    get_document_by_hash,
)


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

PAPERS_DIR = BASE_DIR / "data" / "papers"
DB_PATH = str(BASE_DIR / "data" / "chroma_db")
COLLECTION_NAME = "medical_research"

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


# ============================================================
# ENSURE DIRECTORIES EXIST
# ============================================================

PAPERS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# COMPUTE FILE HASH
# ============================================================

def compute_file_hash(file_path):
    """
    Compute SHA-256 hash of a file for duplicate detection.
    """

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            sha256.update(block)

    return sha256.hexdigest()


# ============================================================
# EXTRACT TEXT FROM PDF
# ============================================================

def extract_text_from_pdf(file_path):
    """
    Extract text from a PDF file page by page using pypdf.
    Returns a list of (page_number, text) tuples.
    """

    reader = PdfReader(str(file_path))

    pages = []

    for i, page in enumerate(reader.pages):

        text = page.extract_text()

        if text and text.strip():
            pages.append((i + 1, text.strip()))

    return pages, len(reader.pages)


# ============================================================
# CHUNK TEXT (PAGE-AWARE)
# ============================================================

def chunk_text(pages, chunk_size=CHUNK_SIZE,
               overlap=CHUNK_OVERLAP):
    """
    Split extracted page text into chunks.

    Each chunk preserves the page number it came from.
    Large pages are split with overlap.
    """

    chunks = []
    chunk_index = 0

    for page_number, text in pages:

        # Clean the text
        text = clean_text(text)

        if not text:
            continue

        # If text fits in one chunk
        if len(text) <= chunk_size:

            chunks.append({
                "text": text,
                "page": page_number,
                "chunk": chunk_index,
            })
            chunk_index += 1

        else:
            # Split large pages
            start = 0

            while start < len(text):

                end = start + chunk_size
                chunk_text_content = text[start:end].strip()

                if chunk_text_content:

                    chunks.append({
                        "text": chunk_text_content,
                        "page": page_number,
                        "chunk": chunk_index,
                    })
                    chunk_index += 1

                start += chunk_size - overlap

    return chunks


# ============================================================
# STORE CHUNKS IN CHROMADB
# ============================================================

def store_in_chromadb(chunks, document_id, filename):
    """
    Generate embeddings and upsert chunks into ChromaDB.
    """

    if not chunks:
        return 0

    # Extract text content for embedding
    texts = [c["text"] for c in chunks]

    # Generate embeddings
    print(f"Generating embeddings for {len(texts)} chunks...")

    embeddings = create_embeddings(texts)

    embeddings_list = (
        embeddings.tolist()
        if hasattr(embeddings, "tolist")
        else embeddings
    )

    # Connect to ChromaDB
    client = chromadb.PersistentClient(path=DB_PATH)

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME
    )

    # Build IDs and metadata
    ids = []
    metadatas = []

    for chunk in chunks:

        chunk_id = f"{document_id}_chunk_{chunk['chunk']}"

        ids.append(chunk_id)

        metadatas.append({
            "source": filename,
            "document_id": document_id,
            "page": chunk["page"],
            "chunk": chunk["chunk"],
            "chunk_total": len(chunks),
        })

    # Upsert into ChromaDB
    print(f"Storing {len(chunks)} chunks in ChromaDB...")

    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings_list,
        metadatas=metadatas,
    )

    print(f"Successfully stored {len(chunks)} chunks.")

    return len(chunks)


# ============================================================
# DELETE DOCUMENT FROM CHROMADB
# ============================================================

def delete_from_chromadb(document_id):
    """
    Remove all chunks for a document from ChromaDB.
    """

    try:
        client = chromadb.PersistentClient(path=DB_PATH)

        collection = client.get_collection(
            name=COLLECTION_NAME
        )

        # Find all chunks belonging to this document
        results = collection.get(
            where={"document_id": document_id},
            include=[]
        )

        if results["ids"]:
            collection.delete(ids=results["ids"])
            print(
                f"Deleted {len(results['ids'])} chunks "
                f"for document {document_id}"
            )

    except Exception as e:
        print(f"Error deleting from ChromaDB: {e}")


# ============================================================
# PROCESS PDF — FULL PIPELINE
# ============================================================

def process_pdf(file_path, document_id, filename):
    """
    Full PDF processing pipeline:

    1. Extract text (pypdf)
    2. Clean text (pdf_processor.clean_text)
    3. Chunk text (page-aware)
    4. Generate embeddings (sentence-transformers)
    5. Store in ChromaDB
    6. Update document status in SQLite
    """

    try:

        # ------------------------------------------------
        # Update status to processing
        # ------------------------------------------------

        update_document_status(
            document_id, "processing"
        )

        # ------------------------------------------------
        # 1. Extract text
        # ------------------------------------------------

        print(f"\nExtracting text from: {filename}")

        pages, total_pages = extract_text_from_pdf(
            file_path
        )

        if not pages:
            update_document_status(
                document_id, "error",
                error_message=(
                    "No text could be extracted from "
                    "this PDF. It may be scanned or empty."
                )
            )
            return {
                "success": False,
                "error": (
                    "No text could be extracted. "
                    "The PDF may be scanned or empty."
                )
            }

        print(f"Extracted text from {len(pages)} pages "
              f"(total: {total_pages} pages)")

        # ------------------------------------------------
        # 2-3. Chunk text
        # ------------------------------------------------

        chunks = chunk_text(pages)

        if not chunks:
            update_document_status(
                document_id, "error",
                error_message="No chunks created from text."
            )
            return {
                "success": False,
                "error": "No processable content found."
            }

        print(f"Created {len(chunks)} chunks")

        # ------------------------------------------------
        # 4-5. Embed and store
        # ------------------------------------------------

        chunk_count = store_in_chromadb(
            chunks, document_id, filename
        )

        # ------------------------------------------------
        # 6. Update status
        # ------------------------------------------------

        update_document_status(
            document_id, "ready",
            page_count=total_pages,
            chunk_count=chunk_count
        )

        print(f"\nDocument processed successfully: "
              f"{filename}")

        return {
            "success": True,
            "page_count": total_pages,
            "chunk_count": chunk_count
        }

    except Exception as e:

        error_msg = str(e)
        print(f"Error processing PDF: {error_msg}")

        update_document_status(
            document_id, "error",
            error_message=error_msg
        )

        return {
            "success": False,
            "error": error_msg
        }
