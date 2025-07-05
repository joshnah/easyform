"""
Advanced form filler - backward compatibility module.

This module maintains backward compatibility by re-exporting the main
functionality from the new modular structure.
"""

# Re-export the main function and key classes for backward compatibility
from .form_filler import fill_in_form
from .fill_processor import FillEntry
from .checkbox_processor import CheckboxEntry
from .pattern_detection import DEFAULT_PLACEHOLDER_PATTERN, CHECKBOX_PATTERN, detect_placeholder_patterns
from .text_extraction import extract_form_text
from .text_utils import sanitize_unicode_for_pdf
from .font_manager import (
    normalize_font_name, 
    get_fonts_cache_dir, 
    download_font_from_google_fonts, 
    get_available_font
)

# For backward compatibility, also expose the internal functions
from .fill_processor import detect_fill_entries as _detect_fill_entries, process_fill_entries as _process_fill_entries
from .checkbox_processor import (
    detect_checkbox_entries as _detect_checkbox_entries,
    process_checkbox_entries as _process_checkbox_entries,
    update_checkbox_in_paragraph as _update_checkbox_in_paragraph
)
from .docx_filler import fill_docx as _fill_docx
from .pdf_filler import fill_pdf as _fill_pdf, fill_flat_pdf as _fill_flat_pdf

__all__ = [
    'fill_in_form',
    'FillEntry',
    'CheckboxEntry', 
    'DEFAULT_PLACEHOLDER_PATTERN',
    'CHECKBOX_PATTERN',
    'detect_placeholder_patterns',
    'extract_form_text',
    'sanitize_unicode_for_pdf',
    'normalize_font_name',
    'get_fonts_cache_dir',
    'download_font_from_google_fonts',
    'get_available_font'
] 