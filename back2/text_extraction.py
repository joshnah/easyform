"""Text extraction utilities — single source of truth for reading documents/context."""

import json as _json
import os
from pathlib import Path


def extract_text_from_file(file_path: str) -> str:
    """
    Extract text from a file. Supports .pdf, .docx, .txt, .md, .json.

    Returns "" for unsupported extensions; raises only for I/O failures
    inside a supported extractor.
    """
    file_path = os.path.abspath(file_path)
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    if ext == ".docx":
        return extract_text_from_docx(file_path)
    if ext in (".txt", ".md"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    if ext == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            return _json.dumps(_json.load(f), indent=2)
    return ""


def extract_text_from_pdf(pdf_path: str) -> str:
    try:
        import fitz  # PyMuPDF
    except ImportError as e:
        raise ImportError(
            "PyMuPDF is required for PDF text extraction (pip install PyMuPDF)"
        ) from e

    doc = fitz.open(pdf_path)
    try:
        return "\n".join(doc.load_page(i).get_text() for i in range(len(doc))).strip()
    finally:
        doc.close()


def extract_text_from_docx(docx_path: str) -> str:
    try:
        from docx import Document
    except ImportError as e:
        raise ImportError(
            "python-docx is required for DOCX text extraction (pip install python-docx)"
        ) from e

    doc = Document(docx_path)
    return "\n".join(p.text for p in doc.paragraphs).strip()
