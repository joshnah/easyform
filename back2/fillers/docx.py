import os

from back2.fillers.base import BaseFiller, FillResult, ensure_ext


class DocxFiller(BaseFiller):
    def _save(self, fill_result: FillResult, output_path: str) -> None:
        out = ensure_ext(output_path, "docx")
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)

        try:
            from docx import Document as DocxDocument
        except ImportError as e:
            raise ImportError(
                "python-docx is required for DOCX output (pip install python-docx)"
            ) from e

        doc = DocxDocument()
        for line in fill_result.filled_text.splitlines():
            doc.add_paragraph(line)
        doc.save(out)
