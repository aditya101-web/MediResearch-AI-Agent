import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

from database import (
    init_db,
    create_document,
    get_document,
    get_document_by_hash,
    get_all_documents,
    delete_document as db_delete_document,
    create_conversation,
    get_conversation,
    get_all_conversations,
    update_conversation_title,
    delete_conversation as db_delete_conversation,
    add_message,
    add_document_to_conversation,
    get_document_ids_for_conversation,
)

# ============================================================
# PATHS
# ============================================================

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


# ============================================================
# MEDIRESEARCH AI - API
# ============================================================

app = FastAPI(
    title="MediResearch AI",
    description="AI-powered medical research assistant",
    version="2.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# INITIALIZE DATABASE ON STARTUP
# ============================================================

@app.on_event("startup")
def startup():
    init_db()
    print("MediResearch AI API ready.")


# ============================================================
# SERVE FRONTEND STATIC FILES
# ============================================================

app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_DIR)),
    name="static"
)


# ============================================================
# REQUEST MODELS
# ============================================================

class QuestionRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None


class ConversationCreate(BaseModel):
    title: Optional[str] = "New Chat"


class ConversationUpdate(BaseModel):
    title: str


# ============================================================
# HOME — SERVE FRONTEND
# ============================================================

@app.get("/")
def home():
    return FileResponse(
        str(FRONTEND_DIR / "index.html")
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():
    return {
        "message": "MediResearch AI API is running!"
    }


# ============================================================
# ASK QUESTION
# ============================================================

@app.post("/ask")
def ask_question(request: QuestionRequest):

    # Lazy import to prevent heavy ML dependencies
    # from loading during application startup
    from rag_pipeline import run_rag

    # Remove unnecessary spaces
    question = request.question.strip()

    # Validate question
    if not question:
        return {
            "error": "Question cannot be empty."
        }

    # Get document IDs for conversation scope
    document_ids = None

    if request.conversation_id:
        document_ids = get_document_ids_for_conversation(
            request.conversation_id
        )

        # If conversation has no documents, search all
        if not document_ids:
            document_ids = None

    # Run RAG pipeline
    result = run_rag(
        question,
        document_ids=document_ids
    )

    answer = result.get("answer", "")
    sources = result.get("sources", [])

    # Save messages to database if conversation exists
    if request.conversation_id:

        # Save user message
        add_message(
            request.conversation_id,
            "user",
            question
        )

        # Save AI message
        add_message(
            request.conversation_id,
            "ai",
            answer,
            sources=sources
        )

    # Return response to frontend
    return {
        "question": question,
        "answer": answer,
        "sources": sources,
        "conversation_id": request.conversation_id
    }


# ============================================================
# DOCUMENT UPLOAD
# ============================================================

@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    conversation_id: Optional[str] = Form(None)
):

    # Lazy import to prevent heavy ML dependencies
    # from loading during application startup
    from document_processor import (
        compute_file_hash,
        process_pdf,
        PAPERS_DIR,
        MAX_FILE_SIZE,
    )

    # --------------------------------------------------------
    # Validate file type
    # --------------------------------------------------------

    if not file.filename:
        return {"error": "No file provided."}

    if not file.filename.lower().endswith(".pdf"):
        return {
            "error": "Only PDF files are accepted."
        }

    # Validate content type
    if file.content_type and \
       file.content_type != "application/pdf":

        # Some browsers may not send correct content type
        # so only reject if explicitly wrong
        if "pdf" not in file.content_type.lower():
            return {
                "error": "Invalid file type. Only PDFs."
            }

    # --------------------------------------------------------
    # Read file and validate size
    # --------------------------------------------------------

    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        return {
            "error": (
                f"File too large. Maximum size is "
                f"{MAX_FILE_SIZE // (1024*1024)} MB."
            )
        }

    if len(content) == 0:
        return {"error": "File is empty."}

    # --------------------------------------------------------
    # Save to temp location and compute hash
    # --------------------------------------------------------

    safe_filename = (
        str(uuid.uuid4())[:8]
        + "_"
        + "".join(
            c for c in file.filename
            if c.isalnum() or c in "._- "
        )
    )

    file_path = PAPERS_DIR / safe_filename

    with open(file_path, "wb") as f:
        f.write(content)

    file_hash = compute_file_hash(file_path)

    # --------------------------------------------------------
    # Check for duplicates
    # --------------------------------------------------------

    existing_doc = get_document_by_hash(file_hash)

    if existing_doc:

        # Remove the just-saved duplicate file
        file_path.unlink(missing_ok=True)

        # Associate with conversation if provided
        if conversation_id:
            add_document_to_conversation(
                conversation_id,
                existing_doc["id"]
            )

        return {
            "document": existing_doc,
            "duplicate": True,
            "message": (
                "This document has already been uploaded "
                "and processed."
            )
        }

    # --------------------------------------------------------
    # Create document record
    # --------------------------------------------------------

    doc = create_document(
        filename=file.filename,
        file_path=str(file_path),
        file_hash=file_hash,
        file_size=len(content)
    )

    # Associate with conversation if provided
    if conversation_id:
        add_document_to_conversation(
            conversation_id,
            doc["id"]
        )

    # --------------------------------------------------------
    # Process the PDF
    # --------------------------------------------------------

    result = process_pdf(
        file_path,
        doc["id"],
        file.filename
    )

    # Refresh document data
    doc = get_document(doc["id"])

    if result["success"]:
        return {
            "document": doc,
            "duplicate": False,
            "message": "Document uploaded and processed."
        }
    else:
        return {
            "document": doc,
            "duplicate": False,
            "error": result.get(
                "error",
                "Processing failed."
            )
        }


# ============================================================
# DOCUMENTS — LIST / GET / DELETE
# ============================================================

@app.get("/api/documents")
def list_documents():
    return {
        "documents": get_all_documents()
    }


@app.get("/api/documents/{doc_id}")
def get_document_info(doc_id: str):

    doc = get_document(doc_id)

    if not doc:
        return {
            "error": "Document not found."
        }

    return {
        "document": doc
    }


@app.delete("/api/documents/{doc_id}")
def delete_document_endpoint(doc_id: str):

    # Lazy import to prevent heavy ML dependencies
    # from loading during application startup
    from document_processor import delete_from_chromadb

    doc = get_document(doc_id)

    if not doc:
        return {
            "error": "Document not found."
        }

    # Delete from ChromaDB
    delete_from_chromadb(doc_id)

    # Delete file from disk
    try:
        file_path = Path(doc["file_path"])

        if file_path.exists():
            file_path.unlink()

    except Exception as e:
        print(f"Error deleting file: {e}")

    # Delete from database
    db_delete_document(doc_id)

    return {
        "message": "Document deleted.",
        "id": doc_id
    }


# ============================================================
# CONVERSATIONS — CRUD
# ============================================================

@app.post("/api/conversations")
def create_conversation_endpoint(
    data: ConversationCreate
):

    conv = create_conversation(data.title)

    return {
        "conversation": conv
    }


@app.get("/api/conversations")
def list_conversations():
    return {
        "conversations": get_all_conversations()
    }


@app.get("/api/conversations/{conv_id}")
def get_conversation_endpoint(conv_id: str):

    conv = get_conversation(conv_id)

    if not conv:
        return {
            "error": "Conversation not found."
        }

    return {
        "conversation": conv
    }


@app.delete("/api/conversations/{conv_id}")
def delete_conversation_endpoint(conv_id: str):

    conv = get_conversation(conv_id)

    if not conv:
        return {
            "error": "Conversation not found."
        }

    db_delete_conversation(conv_id)

    return {
        "message": "Conversation deleted.",
        "id": conv_id
    }


@app.put("/api/conversations/{conv_id}")
def update_conversation_endpoint(
    conv_id: str,
    data: ConversationUpdate
):

    conv = get_conversation(conv_id)

    if not conv:
        return {
            "error": "Conversation not found."
        }

    update_conversation_title(
        conv_id,
        data.title
    )

    return {
        "message": "Conversation updated."
    }


# ============================================================
# ASSOCIATE DOCUMENT WITH CONVERSATION
# ============================================================

@app.post("/api/conversations/{conv_id}/documents")
def add_doc_to_conversation(
    conv_id: str,
    document_id: str = Form(...)
):

    conv = get_conversation(conv_id)

    if not conv:
        return {
            "error": "Conversation not found."
        }

    doc = get_document(document_id)

    if not doc:
        return {
            "error": "Document not found."
        }

    add_document_to_conversation(
        conv_id,
        document_id
    )

    return {
        "message": "Document associated with conversation."
    }