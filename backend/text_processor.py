import re
from pathlib import Path


def clean_text(text):
    """
    Clean extracted PDF text.
    """

    # Remove unwanted control characters
    text = re.sub(r"[\x00-\x1F\x7F]", " ", text)

    # Replace multiple spaces with a single space
    text = re.sub(r"\s+", " ", text)

    # Remove spaces at the beginning and end
    text = text.strip()

    return text


def process_text_file(input_path, output_path):
    """
    Read raw text, clean it, and save the cleaned text.
    """

    text = Path(input_path).read_text(encoding="utf-8")

    cleaned_text = clean_text(text)

    Path(output_path).write_text(
        cleaned_text,
        encoding="utf-8"
    )

    return cleaned_text


if __name__ == "__main__":

    input_path = "../data/processed/sample.txt"
    output_path = "../data/processed/sample_clean.txt"

    print("Cleaning medical research text...")

    cleaned_text = process_text_file(
        input_path,
        output_path
    )

    print("Text cleaning completed!")
    print(f"Saved cleaned text to: {output_path}")