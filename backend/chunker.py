import re
from pathlib import Path


def create_chunks(text, chunk_size=1000, overlap=200):
    """
    Create page-aware and topic-aware chunks.

    Each numbered research topic is treated as a separate chunk.
    Page numbers are extracted directly from the page markers.
    """

    chunks = []

    # --------------------------------------------------
    # Split text using the ACTUAL page number
    #
    # Example:
    # --- Page 2 ---
    # some text
    # --- Page 3 ---
    # some text
    # --------------------------------------------------

    page_parts = re.split(
        r"---\s*Page\s+(\d+)\s*---",
        text,
        flags=re.IGNORECASE
    )

    # page_parts looks like:
    #
    # [text_before_page,
    #  "2", page_2_text,
    #  "3", page_3_text,
    #  "4", page_4_text, ...]


    # --------------------------------------------------
    # Process each page
    # --------------------------------------------------

    for i in range(1, len(page_parts), 2):

        page_number = int(page_parts[i])
        page_text = page_parts[i + 1].strip()

        if not page_text:
            continue

        # --------------------------------------------------
        # Split page into numbered research topics
        #
        # Example:
        #
        # 1. Frailty indices...
        # 2. Spinal anaesthesia...
        # 3. BIS monitoring...
        # --------------------------------------------------

        topics = re.split(
            r"(?=\b\d+\.\s+)",
            page_text
        )

        for topic in topics:

            topic = topic.strip()

            if not topic:
                continue

            # --------------------------------------------------
            # Extract research number
            # --------------------------------------------------

            match = re.match(
                r"^(\d+)\.\s+(.*)",
                topic,
                flags=re.DOTALL
            )

            # Ignore text that is not a numbered research topic
            #
            # This removes things such as:
            #
            # ANAESTHESIA S. no. Topic Observational...
            #
            if not match:
                continue

            research_number = match.group(1)
            content = match.group(2).strip()

            if not content:
                continue

            # --------------------------------------------------
            # If topic fits inside one chunk
            # --------------------------------------------------

            if len(content) <= chunk_size:

                chunk = {
                    "text": content,
                    "page": page_number,
                    "chunk": len(chunks),
                    "research_number": research_number
                }

                chunks.append(chunk)

            # --------------------------------------------------
            # If topic is very large, split it
            # --------------------------------------------------

            else:

                start = 0

                while start < len(content):

                    end = start + chunk_size

                    chunk_content = content[start:end].strip()

                    if chunk_content:

                        chunk = {
                            "text": chunk_content,
                            "page": page_number,
                            "chunk": len(chunks),
                            "research_number": research_number
                        }

                        chunks.append(chunk)

                    start += chunk_size - overlap

    return chunks


# --------------------------------------------------
# Process file
# --------------------------------------------------

def process_file(input_path, output_path):

    print("Creating page/topic-aware text chunks...")

    text = Path(input_path).read_text(
        encoding="utf-8"
    )

    chunks = create_chunks(text)

    Path(output_path).parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        for chunk in chunks:

            file.write(
                f"--- CHUNK {chunk['chunk']} ---\n"
            )

            file.write(
                f"Page: {chunk['page']}\n"
            )

            file.write(
                f"Research Number: {chunk['research_number']}\n"
            )

            file.write(
                f"Content:\n{chunk['text']}\n\n"
            )

    return chunks


# --------------------------------------------------
# Run directly
# --------------------------------------------------

if __name__ == "__main__":

    input_path = "../data/processed/sample_clean.txt"
    output_path = "../data/processed/sample_chunks.txt"

    print("Creating page/topic-aware text chunks...")

    chunks = process_file(
        input_path,
        output_path
    )

    print("Chunking completed!")

    print(f"Number of chunks: {len(chunks)}")

    print(f"Saved chunks to: {output_path}")

    # --------------------------------------------------
    # Show first 5 chunks
    # --------------------------------------------------

    print("\n========== SAMPLE CHUNKS ==========")

    for chunk in chunks[:5]:

        print(f"\nChunk: {chunk['chunk']}")

        print(f"Page: {chunk['page']}")

        print(
            f"Research Number: "
            f"{chunk['research_number']}"
        )

        print(
            f"Content: "
            f"{chunk['text']}"
        )

        print("-" * 50)