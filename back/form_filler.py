"""
Main form filler module.

This module provides the main entry point for form filling functionality,
coordinating all the specialized modules for different file formats and operations.
"""

import os
from typing import List, Optional, Literal
from .text_extraction import extract_form_text
from .pattern_detection import detect_placeholder_patterns
from .docx_filler import fill_docx
from .pdf_filler import fill_pdf


def fill_in_form(
        keys: List[str], form_path: str, context_dir: str, 
        provider: Literal["openai", "groq", "anythingllm"],
        output_path: Optional[str] = None
    ) -> str:
    """
    Advanced form filler using LLM-based detection and filling.
    Supports both DOCX and PDF formats.
    
    Args:
        keys: List of context keys to use for filling
        form_path: Path to the form file to fill
        context_dir: Directory containing context files
        output_path: Optional output path for the filled form
        
    Returns:
        Path to the filled form file
    """
    # Extract form text for pattern analysis
    form_text = extract_form_text(form_path)
    
    # Detect placeholder patterns dynamically
    placeholder_pattern = detect_placeholder_patterns(form_text, provider)
    
    ext = os.path.splitext(form_path)[1].lower()
    if ext == '.docx':
        return fill_docx(keys, form_path, context_dir, output_path, placeholder_pattern, provider)
    elif ext == '.pdf':
        return fill_pdf(keys, form_path, context_dir, output_path, placeholder_pattern, provider)
    else:
        raise ValueError(f"Unsupported form format: {ext}") 