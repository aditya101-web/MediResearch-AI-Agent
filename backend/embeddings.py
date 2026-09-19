from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer


# ============================================================
# Configuration
# ============================================================

MODEL_NAME = "all-MiniLM-L6-v2"

# Project root = MediResearch-AI/
BASE_DIR = Path(__file__).resolve().parent.parent

# Input chunk file
CHUNKS_PATH = BASE_DIR / "data" / "processed" / "sample_chunks.txt"

# Output embeddings
EMBEDDINGS_PATH = BASE_DIR / "data" / "processed" / "sample_embeddings.npy"


# ============================================================
# Load chunks
# ============================================================

def load_chunks(file_path):
    """
    Load topic-aware chunks from sample_chunks.txt.

    Each chunk contains:
        CHUNK number
        Page
        Research Number
        Content
    """

    text = Path(file_path).read_text(encoding="utf-8")

    raw_chunks = text.split("--- CHUNK ")

    chunks = []

    for raw_chunk in raw_chunks:

        raw_chunk = raw_chunk.strip()

        if not raw_chunk:
            continue

        # ----------------------------------------------------
        # Extract Content
        # ----------------------------------------------------

        if "Content:" in raw_chunk:

            content = raw_chunk.split(
                "Content:",
                1
            )[1].strip()

        else:
            content = raw_chunk

        if content:
            chunks.append(content)

    return chunks


# ============================================================
# Cached model singleton
# ============================================================

_model = None


def _get_model():
    """
    Return a cached SentenceTransformer model instance.
    Loaded once on first call, reused thereafter.
    """
    global _model
    if _model is None:
        print(f"\nLoading embedding model: {MODEL_NAME}")
        _model = SentenceTransformer(MODEL_NAME)
        print("Embedding model loaded.")
    return _model


# ============================================================
# Create embeddings
# ============================================================

def create_embeddings(chunks):
    """
    Convert every text chunk into a vector embedding.
    """

    model = _get_model()

    print(f"\nCreating embeddings for {len(chunks)} chunks...")

    embeddings = model.encode(
        chunks,
        show_progress_bar=True,
        convert_to_numpy=True
    )

    return embeddings


# ============================================================
# Save embeddings
# ============================================================

def save_embeddings(embeddings, output_path):
    """
    Save embeddings as a NumPy file.
    """

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    np.save(
        output_path,
        embeddings
    )

    print(
        f"\nEmbeddings saved to: {output_path}"
    )


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("       MEDIRESEARCH AI - EMBEDDING GENERATION")
    print("=" * 60)

    # --------------------------------------------------------
    # Check input file
    # --------------------------------------------------------

    print(f"\nReading chunks from:")
    print(CHUNKS_PATH)

    if not CHUNKS_PATH.exists():

        print("\nERROR: Chunk file not found!")
        print(f"Expected location: {CHUNKS_PATH}")

        raise FileNotFoundError(
            f"Chunk file not found: {CHUNKS_PATH}"
        )

    # --------------------------------------------------------
    # Load chunks
    # --------------------------------------------------------

    chunks = load_chunks(CHUNKS_PATH)

    print(
        f"\nNumber of chunks loaded: {len(chunks)}"
    )

    if not chunks:

        print("\nERROR: No chunks found!")

        raise ValueError(
            "No chunks were found in the chunk file."
        )

    # --------------------------------------------------------
    # Display sample chunks
    # --------------------------------------------------------

    print("\n========== SAMPLE CHUNKS ==========")

    for index, chunk in enumerate(chunks[:5]):

        print(f"\nChunk {index}:")
        print(chunk)

        print("-" * 50)

    # --------------------------------------------------------
    # Create embeddings
    # --------------------------------------------------------

    embeddings = create_embeddings(chunks)

    # --------------------------------------------------------
    # Display embedding information
    # --------------------------------------------------------

    print("\n========== EMBEDDING INFORMATION ==========")

    print(
        f"Number of vectors: {len(embeddings)}"
    )

    print(
        f"Vector dimensions: {embeddings.shape[1]}"
    )

    print(
        f"Embedding shape: {embeddings.shape}"
    )

    # --------------------------------------------------------
    # Save embeddings
    # --------------------------------------------------------

    save_embeddings(
        embeddings,
        EMBEDDINGS_PATH
    )

    # --------------------------------------------------------
    # Finished
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("Embedding generation completed successfully!")
    print("=" * 60)