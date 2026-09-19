import re
import chromadb

from embeddings import create_embeddings, load_chunks


# ============================================================
# CONFIGURATION
# ============================================================

DB_PATH = "../data/chroma_db"
COLLECTION_NAME = "medical_research"

CHUNK_FILE = "../data/processed/sample_chunks.txt"


# ============================================================
# LOAD METADATA
# ============================================================

def load_metadata(file_path):
    """
    Read page number and research number directly
    from sample_chunks.txt.
    """

    print("Reading metadata from chunk file...")

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Split into individual chunks
    raw_chunks = [
        c.strip()
        for c in re.split(r"--- CHUNK \d+ ---", text)
        if c.strip()
    ]

    metadata = []

    for index, chunk in enumerate(raw_chunks):

        # Extract Page number
        page_match = re.search(
            r"Page:\s*(\d+)",
            chunk,
            re.IGNORECASE
        )

        # Extract Research Number
        research_match = re.search(
            r"Research Number:\s*(\d+)",
            chunk,
            re.IGNORECASE
        )

        # Warn if metadata is missing
        if not page_match:
            print(
                f"WARNING: Page number missing for chunk {index}"
            )

        if not research_match:
            print(
                f"WARNING: Research number missing for chunk {index}"
            )

        page = (
            int(page_match.group(1))
            if page_match
            else None
        )

        research_number = (
            int(research_match.group(1))
            if research_match
            else None
        )

        metadata.append({
            "source": "sample.pdf",
            "chunk": index,
            "page": page,
            "research_number": research_number
        })

    return metadata


# ============================================================
# CREATE VECTOR STORE
# ============================================================

def create_vector_store():

    print()
    print("=" * 55)
    print("       MEDIRESEARCH AI - VECTOR STORE CREATION")
    print("=" * 55)

    # --------------------------------------------------------
    # Load chunks
    # --------------------------------------------------------

    print("\nLoading chunks...")

    chunks = load_chunks(CHUNK_FILE)

    print(f"Number of chunks: {len(chunks)}")

    if not chunks:
        print("ERROR: No chunks found.")
        return

    # --------------------------------------------------------
    # Load metadata
    # --------------------------------------------------------

    metadata = load_metadata(CHUNK_FILE)

    print(f"Number of metadata records: {len(metadata)}")

    if len(metadata) != len(chunks):
        print(
            "WARNING: Number of chunks and metadata records "
            "do not match!"
        )
        return

    # --------------------------------------------------------
    # Generate embeddings
    # --------------------------------------------------------

    print("\nGenerating embeddings...")

    embeddings = create_embeddings(chunks)

    embeddings_list = (
        embeddings.tolist()
        if hasattr(embeddings, "tolist")
        else embeddings
    )

    # --------------------------------------------------------
    # Connect to ChromaDB
    # --------------------------------------------------------

    print("\nConnecting to ChromaDB...")

    client = chromadb.PersistentClient(
        path=DB_PATH
    )

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME
    )

    # --------------------------------------------------------
    # Create IDs
    # --------------------------------------------------------

    ids = [
        f"chunk_{i}"
        for i in range(len(chunks))
    ]

    # --------------------------------------------------------
    # Store documents + embeddings + metadata
    # --------------------------------------------------------

    print(
        "\nAdding documents and vectors to ChromaDB..."
    )

    collection.upsert(
        ids=ids,
        documents=chunks,
        embeddings=embeddings_list,
        metadatas=metadata
    )

    # --------------------------------------------------------
    # Verify
    # --------------------------------------------------------

    print("\nVector database created successfully!")

    print(
        f"Documents stored: {collection.count()}"
    )

    # --------------------------------------------------------
    # Metadata verification
    # --------------------------------------------------------

    print()
    print("=" * 55)
    print("              METADATA CHECK")
    print("=" * 55)

    stored_data = collection.get(
        limit=5,
        include=["metadatas"]
    )

    for i, item in enumerate(
        stored_data["metadatas"]
    ):

        print(
            f"Chunk {item.get('chunk')} | "
            f"Page={item.get('page')} | "
            f"Research={item.get('research_number')}"
        )

    print("=" * 55)


# ============================================================
# RUN PROGRAM
# ============================================================

if __name__ == "__main__":
    create_vector_store()