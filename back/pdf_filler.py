"""
PDF form filling functionality.

This module handles filling of PDF forms, including both interactive forms
and flat PDF text overlay filling.
"""

import os
import re
import json
import logging
from typing import List, Optional
from pypdf import PdfReader, PdfWriter
import fitz
from typing import Literal 
from .font_manager import get_available_font, get_fonts_cache_dir
from .fill_processor import detect_fill_entries, process_fill_entries, FillEntry
from .text_utils import sanitize_unicode_for_pdf
from .context_extractor import extract_context
from .checkbox_processor import CheckboxEntry


def fill_pdf(
    keys: List[str],
    form_path: str,
    context_dir: str,
    output_path: Optional[str],
    placeholder_pattern,
    provider: Literal["openai", "groq", "anythingllm"]
) -> str:
    """
    Fill an interactive PDF form by mapping context_data keys to field names.
    If no AcroForm is present, fall back to flat PDF filling.
    """
    # Load or extract context data
    context_path = os.path.join(context_dir, "context_data.json")
    if os.path.exists(context_path):
        with open(context_path, "r", encoding="utf-8") as f:
            context_data = json.load(f)
    else:
        context_data = extract_context(context_dir, provider)

    # Attempt interactive form fill
    reader = PdfReader(form_path)
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)

    try:
        writer.update_page_form_field_values(None, context_data)
        # Save interactive-filled PDF
        out = output_path or form_path.replace(".pdf", "_filled.pdf")
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        with open(out, "wb") as f:
            writer.write(f)
        return out
    except Exception as e:
        logging.info(
            f"No interactive form or fill failed: {e}, falling back to flat PDF fill."
        )
        # Fall back to flat PDF fill
        return fill_flat_pdf(
            keys, form_path, context_dir, output_path, placeholder_pattern, provider
        )


def fill_flat_pdf(
    keys: List[str],
    form_path: str,
    context_dir: str,
    output_path: Optional[str],
    placeholder_pattern,
    provider: Literal["openai", "groq", "anythingllm"]
) -> str:
    """Fill placeholders in a flat PDF by overlaying text at placeholder locations."""
    # Open PDF with PyMuPDF
    doc = fitz.open(form_path)
    cache_dir = get_fonts_cache_dir()

    for page in doc:
        # Font resolution cache to avoid repeated lookups within the page
        font_cache = {}

        # Extract text lines and positions
        lines_data = []
        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                text_line = "".join(span.get("text", "") for span in spans)
                # Compute bounding rect for line
                xs = [b for span in spans for b in (span["bbox"][0], span["bbox"][2])]
                ys = [b for span in spans for b in (span["bbox"][1], span["bbox"][3])]
                rect = (min(xs), min(ys), max(xs), max(ys))
                lines_data.append({"text": text_line, "spans": spans, "rect": rect})

        lines = [ld["text"] for ld in lines_data]
        # Detect and process fill entries
        entries = detect_fill_entries(lines, keys, placeholder_pattern, provider)
        entries = process_fill_entries(
            entries, context_dir, placeholder_pattern, provider
        )

        # Redact original placeholders
        for entry in entries:
            group = entry.lines.split("\n")
            n = len(group)
            for i in range(len(lines) - n + 1):
                if lines[i : i + n] == group:
                    for j in range(n):
                        rd_rect = fitz.Rect(lines_data[i + j]["rect"])
                        page.add_redact_annot(rd_rect, fill=(1, 1, 1))
                    break
        page.apply_redactions()

        # Draw filled text
        for entry in entries:
            group = entry.lines.split("\n")
            filled = entry.filled_lines.split("\n")
            n = len(group)
            for i in range(len(lines) - n + 1):
                if lines[i : i + n] == group:
                    for j in range(n):
                        span0 = lines_data[i + j]["spans"][0]
                        x = span0["bbox"][0]  # Left edge
                        # Use the bottom of the bounding box as baseline position
                        # This ensures text is positioned at the same level as original
                        y = span0["bbox"][3]  # Bottom edge (closer to baseline)
                        fontsize = span0.get("size", 12)
                        # Sanitize Unicode characters that may not render properly
                        sanitized_text = sanitize_unicode_for_pdf(filled[j])

                        # Extract font from this specific span
                        original_font_name = span0.get("font", "")
                        if original_font_name:
                            # Clean up font name (remove subset prefixes like "ABCDEF+")
                            original_font_name = re.sub(
                                r"^[A-Z]{6}\+", "", original_font_name
                            )

                        # Use font cache to avoid repeated resolution
                        if original_font_name and original_font_name not in font_cache:
                            font_name, font_file_path = get_available_font(
                                original_font_name, cache_dir
                            )
                            font_cache[original_font_name] = (font_name, font_file_path)
                            logging.debug(
                                f"Resolved font for PDF span: {original_font_name} → {font_name}"
                            )
                        elif original_font_name:
                            font_name, font_file_path = font_cache[original_font_name]
                        else:
                            # No font info available, use fallback
                            font_name, font_file_path = "helv", None

                        # Try to use the detected font with fallback chain
                        text_inserted = False

                        # If we have a font file, try to load it
                        if font_file_path and os.path.exists(font_file_path):
                            try:
                                # Load custom font file
                                fontbuffer = open(font_file_path, "rb").read()
                                font = fitz.Font(fontbuffer=fontbuffer)
                                page.insert_text(
                                    (x, y),
                                    sanitized_text,
                                    font=font,
                                    fontsize=fontsize,
                                    color=(0, 0, 0),
                                )
                                text_inserted = True
                                logging.debug(
                                    f"Used custom font file for span: {font_file_path}"
                                )
                            except Exception as e:
                                logging.debug(
                                    f"Failed to use custom font file {font_file_path}: {e}"
                                )

                        # If custom font failed, try system font name
                        if not text_inserted:
                            try:
                                page.insert_text(
                                    (x, y),
                                    sanitized_text,
                                    fontname=font_name,
                                    fontsize=fontsize,
                                    color=(0, 0, 0),
                                )
                                text_inserted = True
                                logging.debug(f"Used system font for span: {font_name}")
                            except Exception as e:
                                logging.debug(
                                    f"Failed to use system font {font_name}: {e}"
                                )

                        # Final fallback to Arial
                        if not text_inserted:
                            try:
                                page.insert_text(
                                    (x, y),
                                    sanitized_text,
                                    fontname="Arial",
                                    fontsize=fontsize,
                                    color=(0, 0, 0),
                                )
                                text_inserted = True
                                logging.debug("Used Arial fallback for span")
                            except Exception as e:
                                logging.debug(f"Failed to use Arial: {e}")

                        # Ultimate fallback to helv
                        if not text_inserted:
                            try:
                                page.insert_text(
                                    (x, y),
                                    sanitized_text,
                                    fontname="helv",
                                    fontsize=fontsize,
                                    color=(0, 0, 0),
                                )
                                logging.debug("Used helv fallback for span")
                            except Exception as e:
                                logging.error(f"All font options failed: {e}")
                    break

    # Save output PDF
    out = output_path or form_path.replace(".pdf", "_filled.pdf")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    # Ensure we're not overwriting the original file
    if os.path.abspath(out) == os.path.abspath(form_path):
        out = form_path.replace(".pdf", "_filled.pdf")
    doc.save(out, incremental=False, encryption=fitz.PDF_ENCRYPT_NONE)
    doc.close()
    return out


def fill_pdf_with_entries(
    fill_entries: List[FillEntry],
    checkbox_entries: List[CheckboxEntry],
    form_path: str,
    output_path: Optional[str] = None,
) -> str:
    """Fill a PDF (interactive or flat) using pre-computed FillEntry / CheckboxEntry lists.
    Currently, checkbox_entries are accepted for compatibility but are **ignored** because PDF overlay
    logic is not yet implemented for checkboxes. Future work can extend this.
    """
    return fill_flat_pdf_with_entries(fill_entries, form_path, output_path)


def fill_flat_pdf_with_entries(
    fill_entries: List[FillEntry], form_path: str, output_path: Optional[str]
) -> str:
    """Overlay filled text using a straightforward find-and-replace strategy.

    For every line in the PDF we perform *in-place* substitution of all occurrences of
    each placeholder from ``entry.lines`` with its corresponding replacement from
    ``entry.filled_lines``.  The rest of the line (and page) remains unchanged.

    We redact the entire line once (if any substitution occurred) and re-draw the
    *updated* line, avoiding text overlap and ensuring other lines stay intact.
    """

    import fitz
    import re

    cache_dir = get_fonts_cache_dir()
    doc = fitz.open(form_path)

    for page in doc:  # type: fitz.Page
        font_cache = {}

        # Extract line information for the page
        lines_data = []
        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:
                continue  # Skip non-text blocks
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                text_line = "".join(span.get("text", "") for span in spans)
                xs = [b for span in spans for b in (span["bbox"][0], span["bbox"][2])]
                ys = [b for span in spans for b in (span["bbox"][1], span["bbox"][3])]
                rect = (min(xs), min(ys), max(xs), max(ys))
                lines_data.append({"text": text_line, "spans": spans, "rect": rect})

        # Determine modifications for each line **once**
        modified_lines = {}
        for idx, ld in enumerate(lines_data):
            new_text = ld["text"]
            for entry in fill_entries:
                groups = entry.lines.split("\n")
                filled = entry.filled_lines.split("\n")
                # Pad filled if needed
                if len(filled) < len(groups):
                    filled.extend(["" for _ in range(len(groups) - len(filled))])
                for g_idx, group_line in enumerate(groups):
                    if group_line:
                        new_text = new_text.replace(group_line, filled[g_idx])
            if new_text != ld["text"]:
                modified_lines[idx] = new_text

        # Redact all lines that changed
        for idx in modified_lines:
            rect = fitz.Rect(lines_data[idx]["rect"])
            page.add_redact_annot(rect, fill=(1, 1, 1))
        if modified_lines:
            page.apply_redactions()

        # Re-draw modified lines
        for idx, new_text in modified_lines.items():
            span0 = lines_data[idx]["spans"][0]
            x = span0["bbox"][0]
            y = span0["bbox"][3]
            fontsize = span0.get("size", 12)
            sanitized_text = sanitize_unicode_for_pdf(new_text)

            original_font_name = span0.get("font", "")
            if original_font_name:
                original_font_name = re.sub(r"^[A-Z]{6}\+", "", original_font_name)

            # Resolve a usable font
            if original_font_name and original_font_name not in font_cache:
                font_name, font_file_path = get_available_font(original_font_name, cache_dir)
                font_cache[original_font_name] = (font_name, font_file_path)
            elif original_font_name:
                font_name, font_file_path = font_cache[original_font_name]
            else:
                font_name, font_file_path = "helv", None

            text_inserted = False
            if font_file_path and os.path.exists(font_file_path):
                try:
                    fontbuffer = open(font_file_path, "rb").read()
                    font = fitz.Font(fontbuffer=fontbuffer)
                    page.insert_text((x, y), sanitized_text, font=font, fontsize=fontsize, color=(0, 0, 0))
                    text_inserted = True
                except Exception:
                    pass

            if not text_inserted:
                try:
                    page.insert_text((x, y), sanitized_text, fontname=font_name, fontsize=fontsize, color=(0, 0, 0))
                    text_inserted = True
                except Exception:
                    pass

            if not text_inserted:
                # Final fallback to helv
                try:
                    page.insert_text((x, y), sanitized_text, fontname="helv", fontsize=fontsize, color=(0, 0, 0))
                except Exception:
                    pass

    # Save output PDF
    out = output_path or form_path.replace(".pdf", "_filled.pdf")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    if os.path.abspath(out) == os.path.abspath(form_path):
        out = form_path.replace(".pdf", "_filled.pdf")
    doc.save(out, incremental=False, encryption=fitz.PDF_ENCRYPT_NONE)
    doc.close()
    return out


# Refactor legacy fill_pdf to keep compatibility but delegate


def fill_pdf(
    keys: List[str],
    form_path: str,
    context_dir: str,
    output_path: Optional[str],
    placeholder_pattern,
    provider: Literal["openai", "groq", "anythingllm"]
):
    """Legacy PDF fill: detects entries then delegates to new fill_pdf_with_entries."""
    # Build lines for detection
    import fitz

    doc = fitz.open(form_path)
    lines: List[str] = []
    for page in doc:
        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                text_line = "".join(span.get("text", "") for span in spans)
                lines.append(text_line)
    doc.close()

    entries = detect_fill_entries(lines, keys, placeholder_pattern, provider)
    entries = process_fill_entries(entries, context_dir, placeholder_pattern, provider)

    # PDF checkbox not supported; pass empty list.
    return fill_pdf_with_entries(entries, [], form_path, output_path) 