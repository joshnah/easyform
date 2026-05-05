from typing import Dict, Type, Literal, overload
from back2.form_fillers.base_filler import BaseFiller
from back2.form_fillers.txt_filler import TxtFiller
from back2.form_fillers.docx_filler import DocxFiller
from back2.form_fillers.pdf_filler import PdfFiller

# Filler factory and optional typing overloads for better editor/mypy support
_FILLER_REGISTRY: Dict[str, Type[BaseFiller]] = {
    "txt": TxtFiller,
    "text": TxtFiller,
    "docx": DocxFiller,
    "pdf": PdfFiller,
}


@overload
def get_filler_for_extension(ext: Literal["pdf"]) -> PdfFiller: ...


@overload
def get_filler_for_extension(ext: Literal["docx"]) -> DocxFiller: ...


@overload
def get_filler_for_extension(ext: Literal["txt", "text"]) -> TxtFiller: ...


@overload
def get_filler_for_extension(ext: str) -> BaseFiller: ...


def get_filler_for_extension(ext: str) -> BaseFiller:
    key = (ext or "txt").lower().lstrip(".")
    cls = _FILLER_REGISTRY.get(key, TxtFiller)
    return cls()