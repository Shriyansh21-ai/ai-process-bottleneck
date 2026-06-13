from src.rag.pdf_parser import (
    extract_text_from_pdf
)


def analyze_pdf(input_data: dict):

    path = input_data["path"]

    text = extract_text_from_pdf(
        path
    )

    return {
        "text": text[:5000]
    }