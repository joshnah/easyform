"""filler_agent package."""

# Import and expose the main functionality
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