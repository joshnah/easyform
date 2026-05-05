import os

from back2.fillers.base import BaseFiller, FillResult, ensure_ext

# Page layout constants (approx A4 in PDF points).
PAGE_WIDTH = 595
PAGE_HEIGHT = 842
PAGE_MARGIN = 72
DEFAULT_FONT_SIZE = 12
LINE_HEIGHT = 14
FONT_FALLBACK_SIZE = 12


class PdfFiller(BaseFiller):
    def _save(self, fill_result: FillResult, output_path: str) -> None:
        out = ensure_ext(output_path, "pdf")
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)

        try:
            import fitz  # PyMuPDF
        except ImportError as e:
            raise ImportError("PyMuPDF (fitz) is not available") from e

        doc = fitz.open()
        try:
            page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
            y = PAGE_MARGIN
            for line in fill_result.filled_text.splitlines():
                if y + LINE_HEIGHT > PAGE_HEIGHT - PAGE_MARGIN:
                    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
                    y = PAGE_MARGIN
                _insert_line(page, PAGE_MARGIN, y, line)
                y += LINE_HEIGHT
            doc.save(out, incremental=False)
        finally:
            doc.close()


def _insert_line(page, x: float, y: float, text: str) -> None:
    """Try the default font size, then a fallback, then silently skip the line."""
    for size in (DEFAULT_FONT_SIZE, FONT_FALLBACK_SIZE):
        try:
            page.insert_text((x, y), text, fontsize=size, color=(0, 0, 0))
            return
        except Exception:
            continue
