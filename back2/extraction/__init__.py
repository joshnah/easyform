"""Read documents to text, detect placeholder patterns.

Single source of truth for getting plain text out of PDF / DOCX / TXT / MD /
JSON, plus the regex picker that decides which placeholder shape a form uses.
"""

from back2.extraction.patterns import detect_placeholder_pattern
from back2.extraction.text import (
    extract_text_from_docx,
    extract_text_from_file,
    extract_text_from_pdf,
)

__all__ = [
    "detect_placeholder_pattern",
    "extract_text_from_docx",
    "extract_text_from_file",
    "extract_text_from_pdf",
]
