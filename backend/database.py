import sqlite3
import uuid
import json
from pathlib import Path
from datetime import datetime, timezone


# ============================================================
# DATABASE PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = str(BASE_DIR / "data" / "mediresearch.db")


# ============================================================
# CONNECTION
# ============================================================

def get_connection():
    """
    Get a SQLite connection with row factory enabled.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def init_db():
    """
    Create all tables if they do not exist.
    """

    conn = get_connection()

    conn.executescript("""

        CREATE TABLE IF NOT EXISTS documents (
            id            TEXT PRIMARY KEY,
            filename      TEXT NOT NULL,
            file_path     TEXT NOT NULL,
            file_hash     TEXT NOT NULL UNIQUE,
            file_size     INTEGER NOT NULL,
            page_count    INTEGER,
            chunk_count   INTEGER DEFAULT 0,
            status        TEXT DEFAULT 'pending',
            error_message TEXT,
            created_at    TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS messages (
            id              TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            role            TEXT NOT NULL,
            content         TEXT NOT NULL,
            sources         TEXT,
            created_at      TEXT NOT NULL,
            FOREIGN KEY (conversation_id)
                REFERENCES conversations(id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS conversation_documents (
            conversation_id TEXT NOT NULL,
            document_id     TEXT NOT NULL,
            PRIMARY KEY (conversation_id, document_id),
            FOREIGN KEY (conversation_id)
                REFERENCES conversations(id)
                ON DELETE CASCADE,
            FOREIGN KEY (document_id)
                REFERENCES documents(id)
        );

    """)

    conn.commit()
    conn.close()

    print("Database initialized.")


# ============================================================
# HELPERS
# ============================================================

def _now():
    return datetime.now(timezone.utc).isoformat()


def _new_id():
    return str(uuid.uuid4())


def _row_to_dict(row):
    if row is None:
        return None
    return dict(row)


# ============================================================
# DOCUMENTS — CRUD
# ============================================================

def create_document(filename, file_path, file_hash, file_size):
    """
    Insert a new document record.
    Returns the document dict.
    """

    doc_id = _new_id()
    now = _now()

    conn = get_connection()

    conn.execute(
        """
        INSERT INTO documents
            (id, filename, file_path, file_hash,
             file_size, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'pending', ?)
        """,
        (doc_id, filename, file_path, file_hash,
         file_size, now)
    )

    conn.commit()
    doc = _row_to_dict(
        conn.execute(
            "SELECT * FROM documents WHERE id = ?",
            (doc_id,)
        ).fetchone()
    )
    conn.close()

    return doc


def get_document(doc_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM documents WHERE id = ?",
        (doc_id,)
    ).fetchone()
    conn.close()
    return _row_to_dict(row)


def get_document_by_hash(file_hash):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM documents WHERE file_hash = ?",
        (file_hash,)
    ).fetchone()
    conn.close()
    return _row_to_dict(row)


def get_all_documents():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM documents ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def update_document_status(doc_id, status,
                           page_count=None,
                           chunk_count=None,
                           error_message=None):
    conn = get_connection()

    if status == "ready":
        conn.execute(
            """
            UPDATE documents
            SET status = ?, page_count = ?,
                chunk_count = ?
            WHERE id = ?
            """,
            (status, page_count, chunk_count, doc_id)
        )
    elif status == "error":
        conn.execute(
            """
            UPDATE documents
            SET status = ?, error_message = ?
            WHERE id = ?
            """,
            (status, error_message, doc_id)
        )
    else:
        conn.execute(
            """
            UPDATE documents
            SET status = ?
            WHERE id = ?
            """,
            (status, doc_id)
        )

    conn.commit()
    conn.close()


def delete_document(doc_id):
    conn = get_connection()
    conn.execute(
        "DELETE FROM conversation_documents WHERE document_id = ?",
        (doc_id,)
    )
    conn.execute(
        "DELETE FROM documents WHERE id = ?",
        (doc_id,)
    )
    conn.commit()
    conn.close()


# ============================================================
# CONVERSATIONS — CRUD
# ============================================================

def create_conversation(title="New Chat"):
    conv_id = _new_id()
    now = _now()

    conn = get_connection()

    conn.execute(
        """
        INSERT INTO conversations
            (id, title, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        """,
        (conv_id, title, now, now)
    )

    conn.commit()
    conv = _row_to_dict(
        conn.execute(
            "SELECT * FROM conversations WHERE id = ?",
            (conv_id,)
        ).fetchone()
    )
    conn.close()

    return conv


def get_conversation(conv_id):
    conn = get_connection()

    conv = _row_to_dict(
        conn.execute(
            "SELECT * FROM conversations WHERE id = ?",
            (conv_id,)
        ).fetchone()
    )

    if conv is None:
        conn.close()
        return None

    # Get messages
    messages = conn.execute(
        """
        SELECT * FROM messages
        WHERE conversation_id = ?
        ORDER BY created_at ASC
        """,
        (conv_id,)
    ).fetchall()

    conv["messages"] = []
    for msg in messages:
        m = _row_to_dict(msg)
        # Parse sources JSON
        if m.get("sources"):
            try:
                m["sources"] = json.loads(m["sources"])
            except (json.JSONDecodeError, TypeError):
                m["sources"] = []
        else:
            m["sources"] = []
        conv["messages"].append(m)

    # Get associated documents
    docs = conn.execute(
        """
        SELECT d.* FROM documents d
        JOIN conversation_documents cd
            ON d.id = cd.document_id
        WHERE cd.conversation_id = ?
        ORDER BY d.created_at DESC
        """,
        (conv_id,)
    ).fetchall()

    conv["documents"] = [_row_to_dict(d) for d in docs]

    conn.close()
    return conv


def get_all_conversations():
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT * FROM conversations
        ORDER BY updated_at DESC
        """
    ).fetchall()

    conversations = []

    for row in rows:
        conv = _row_to_dict(row)

        # Get document count
        doc_count = conn.execute(
            """
            SELECT COUNT(*) as cnt
            FROM conversation_documents
            WHERE conversation_id = ?
            """,
            (conv["id"],)
        ).fetchone()

        conv["document_count"] = doc_count["cnt"] if doc_count else 0

        # Get message count
        msg_count = conn.execute(
            """
            SELECT COUNT(*) as cnt
            FROM messages
            WHERE conversation_id = ?
            """,
            (conv["id"],)
        ).fetchone()

        conv["message_count"] = msg_count["cnt"] if msg_count else 0

        conversations.append(conv)

    conn.close()
    return conversations


def update_conversation_title(conv_id, title):
    conn = get_connection()
    conn.execute(
        """
        UPDATE conversations
        SET title = ?, updated_at = ?
        WHERE id = ?
        """,
        (title, _now(), conv_id)
    )
    conn.commit()
    conn.close()


def update_conversation_timestamp(conv_id):
    conn = get_connection()
    conn.execute(
        """
        UPDATE conversations
        SET updated_at = ?
        WHERE id = ?
        """,
        (_now(), conv_id)
    )
    conn.commit()
    conn.close()


def delete_conversation(conv_id):
    conn = get_connection()
    conn.execute(
        "DELETE FROM conversations WHERE id = ?",
        (conv_id,)
    )
    conn.commit()
    conn.close()


# ============================================================
# MESSAGES
# ============================================================

def add_message(conversation_id, role, content,
                sources=None):
    msg_id = _new_id()
    now = _now()

    sources_json = None
    if sources:
        sources_json = json.dumps(sources)

    conn = get_connection()

    conn.execute(
        """
        INSERT INTO messages
            (id, conversation_id, role, content,
             sources, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (msg_id, conversation_id, role, content,
         sources_json, now)
    )

    # Update conversation timestamp
    conn.execute(
        """
        UPDATE conversations
        SET updated_at = ?
        WHERE id = ?
        """,
        (now, conversation_id)
    )

    conn.commit()
    conn.close()

    return {
        "id": msg_id,
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "sources": sources or [],
        "created_at": now
    }


# ============================================================
# CONVERSATION — DOCUMENTS
# ============================================================

def add_document_to_conversation(conversation_id,
                                  document_id):
    conn = get_connection()

    # Check if already associated
    existing = conn.execute(
        """
        SELECT 1 FROM conversation_documents
        WHERE conversation_id = ? AND document_id = ?
        """,
        (conversation_id, document_id)
    ).fetchone()

    if not existing:
        conn.execute(
            """
            INSERT INTO conversation_documents
                (conversation_id, document_id)
            VALUES (?, ?)
            """,
            (conversation_id, document_id)
        )
        conn.commit()

    conn.close()


def get_document_ids_for_conversation(conversation_id):
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT document_id
        FROM conversation_documents
        WHERE conversation_id = ?
        """,
        (conversation_id,)
    ).fetchall()

    conn.close()

    return [row["document_id"] for row in rows]
