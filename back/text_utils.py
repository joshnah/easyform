"""
Text processing utilities for form filling.

This module contains utility functions for text processing, including
Unicode character sanitization for PDF rendering.
"""

import logging


def sanitize_unicode_for_pdf(text: str) -> str:
    """
    Sanitize Unicode characters that may not render properly in PDF fonts.
    Replaces problematic Unicode characters with ASCII equivalents.
    """
    if not text:
        return text
    
    # Track if any replacements were made
    original_text = text
    
    # Unicode character mappings to ASCII equivalents
    unicode_replacements = {
        # Smart quotes
        '\u201c': '"',  # Left double quotation mark (8220)
        '\u201d': '"',  # Right double quotation mark (8221)
        '\u2018': "'",  # Left single quotation mark (8216)
        '\u2019': "'",  # Right single quotation mark (8217)
        
        # Dashes
        '\u2014': '--',  # Em dash (8212)
        '\u2013': '-',   # En dash (8211)
        
        # Other common problematic characters
        '\u2026': '...',  # Horizontal ellipsis (8230)
        '\u00a0': ' ',    # Non-breaking space (160)
    }
    
    # Apply replacements
    for unicode_char, ascii_replacement in unicode_replacements.items():
        text = text.replace(unicode_char, ascii_replacement)
    
    # Log if any replacements were made
    if text != original_text:
        replaced_chars = []
        for unicode_char, ascii_replacement in unicode_replacements.items():
            if unicode_char in original_text:
                replaced_chars.append(f"'{unicode_char}' → '{ascii_replacement}'")
        if replaced_chars:
            logging.debug(f"Sanitized Unicode characters for PDF rendering: {', '.join(replaced_chars)}")
    
    return text 