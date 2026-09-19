import re
from pathlib import Path


def clean_text(text):
    """
    Clean raw text extracted from a medical PDF.
    """

    # Replace control characters with spaces
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", " ", text)

    # Remove excessive spaces while preserving new lines
    text = re.sub(r"[ \t]+", " ", text)

    # Remove excessive blank lines
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    # Remove spaces at the beginning and end
    text = text.strip()

    return text


def process_text_file(input_path, output_path):

    # Read the raw text
    text = Path(input_path).read_text(encoding="utf-8")

    # Clean the text
    cleaned_text = clean_text(text)

    # Save cleaned text
    Path(output_path).write_text(
        cleaned_text,
        encoding="utf-8"
    )

    return cleaned_text


if __name__ == "__main__":

    input_path = "data/processed/sample.txt"
    output_path = "data/processed/sample_clean.txt"

    print("Cleaning medical research text...")

    process_text_file(input_path, output_path)

    print("Cleaning completed!")
    print(f"Saved to: {output_path}")