"""Form fillers — write a filled document to disk.

Native back2 fillers regenerate the document from `filled_text`. Overlay-onto-
original behavior lives in the legacy `back/` package and is exposed via the
compat endpoints in `back2/api/compat.py`.
"""

from typing import Dict, Literal, Type, overload

from back2.fillers.base import BaseFiller, FillResult, ensure_ext
from back2.fillers.docx import DocxFiller
from back2.fillers.pdf import PdfFiller
from back2.fillers.txt import TxtFiller

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
    """Return a filler instance for the given file extension.

    Unknown extensions fall through to `TxtFiller`.
    """
    key = (ext or "txt").lower().lstrip(".")
    cls = _FILLER_REGISTRY.get(key, TxtFiller)
    return cls()


__all__ = [
    "BaseFiller",
    "DocxFiller",
    "FillResult",
    "PdfFiller",
    "TxtFiller",
    "ensure_ext",
    "get_filler_for_extension",
]
