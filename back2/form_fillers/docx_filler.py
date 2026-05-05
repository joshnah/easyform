import os

from back2.form_fillers.base_filler import BaseFiller, FillResult
from back2.form_fillers.utils import ensure_ext

class DocxFiller(BaseFiller):
    def _save(self, fill_result: FillResult, output_path: str) -> None:
        out = ensure_ext(output_path, "docx")
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        try:
            from docx import Document as DocxDocument

            doc = DocxDocument()
            for line in fill_result.filled_text.splitlines():
                doc.add_paragraph(line)
            doc.save(out)

        except Exception as e:
            raise Exception(f"Error saving DOCX file: {e}")
