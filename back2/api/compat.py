"""Legacy compatibility API routes.

Mirror the original `back/api.py` endpoint surface so the existing frontend
and root `test_api_process.py` keep working unchanged. Each handler does a
**lazy** `from back.<module> import …` so module load and `/health` don't
pull in `easyocr` / `docling`.

Once the frontend migrates onto the native surface, this module can be
deleted along with the `back/` package — see `docs/back2/migration.md`.
"""

import re
from typing import List, Literal, Optional, Tuple

from fastapi import APIRouter
from pydantic import BaseModel

from back2.api import context_store

router = APIRouter()

LegacyProvider = Literal["openai", "groq", "anythingllm", "local"]


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class FillEntrySchema(BaseModel):
    lines: str
    number_of_fill_spots: int
    context_keys: List[Optional[str]]
    filled_lines: str = ""

    @classmethod
    def from_dataclass(cls, entry) -> "FillEntrySchema":
        return cls(
            lines=entry.lines,
            number_of_fill_spots=entry.number_of_fill_spots,
            context_keys=entry.context_keys,
            filled_lines=entry.filled_lines,
        )

    def to_dataclass(self):
        from back.fill_processor import FillEntry

        return FillEntry(
            lines=self.lines,
            number_of_fill_spots=self.number_of_fill_spots,
            context_keys=self.context_keys,
            filled_lines=self.filled_lines,
        )


class CheckboxEntrySchema(BaseModel):
    lines: str
    checkbox_positions: List[Tuple[int, int]]
    checkbox_values: List[str]
    context_key: Optional[str] = None
    checked_indices: List[int] = []

    @classmethod
    def from_dataclass(cls, entry) -> "CheckboxEntrySchema":
        return cls(
            lines=entry.lines,
            checkbox_positions=entry.checkbox_positions,
            checkbox_values=entry.checkbox_values,
            context_key=entry.context_key,
            checked_indices=entry.checked_indices or [],
        )

    def to_dataclass(self):
        from back.checkbox_processor import CheckboxEntry

        return CheckboxEntry(
            lines=self.lines,
            checkbox_positions=self.checkbox_positions,
            checkbox_values=self.checkbox_values,
            context_key=self.context_key,
            checked_indices=self.checked_indices,
        )


class ExtractFormTextRequest(BaseModel):
    form_path: str


class ExtractFormTextResponse(BaseModel):
    text: str


class DetectPatternRequest(BaseModel):
    text: str
    provider: LegacyProvider


class DetectPatternResponse(BaseModel):
    pattern: str


class DetectFillEntriesRequest(BaseModel):
    lines: List[str]
    keys: List[str]
    pattern: str
    provider: LegacyProvider


class DetectFillEntriesResponse(BaseModel):
    entries: List[FillEntrySchema]


class ProcessFillEntriesRequest(BaseModel):
    entries: List[FillEntrySchema]
    context_dir: str
    pattern: str
    provider: LegacyProvider


class ProcessFillEntriesResponse(BaseModel):
    entries: List[FillEntrySchema]


class ContextDirRequest(BaseModel):
    context_dir: str


class ContextResponse(BaseModel):
    context: dict


class ContextKeyValueRequest(BaseModel):
    context_dir: str
    key: str
    value: str


class ContextKeyRequest(BaseModel):
    context_dir: str
    key: str


class ExtractContextRequest(BaseModel):
    context_dir: str
    provider: LegacyProvider


class DetectCheckboxEntriesRequest(BaseModel):
    lines: List[str]
    keys: List[str]


class DetectCheckboxEntriesResponse(BaseModel):
    entries: List[CheckboxEntrySchema]


class ProcessCheckboxEntriesRequest(BaseModel):
    entries: List[CheckboxEntrySchema]
    context_dir: str
    keys: List[str]
    provider: LegacyProvider


class ProcessCheckboxEntriesResponse(BaseModel):
    entries: List[CheckboxEntrySchema]


class FillDocxRequest(BaseModel):
    fill_entries: List[FillEntrySchema]
    checkbox_entries: List[CheckboxEntrySchema]
    form_path: str
    output_path: Optional[str] = None


class FillPdfRequest(BaseModel):
    fill_entries: List[FillEntrySchema]
    checkbox_entries: List[CheckboxEntrySchema] = []
    form_path: str
    output_path: Optional[str] = None


class FillFormResponse(BaseModel):
    output_path: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/form/text", response_model=ExtractFormTextResponse)
def api_extract_form_text(req: ExtractFormTextRequest):
    from back.text_extraction import extract_form_text

    return ExtractFormTextResponse(text=extract_form_text(req.form_path))


@router.post("/pattern/detect", response_model=DetectPatternResponse)
def api_detect_pattern(req: DetectPatternRequest):
    from back.pattern_detection import detect_placeholder_patterns

    pattern = detect_placeholder_patterns(req.text, req.provider)
    return DetectPatternResponse(pattern=pattern.pattern)


@router.post("/fill-entries/detect", response_model=DetectFillEntriesResponse)
def api_detect_fill_entries(req: DetectFillEntriesRequest):
    from back.fill_processor import detect_fill_entries

    compiled = re.compile(req.pattern)
    entries = detect_fill_entries(req.lines, req.keys, compiled, req.provider)
    return DetectFillEntriesResponse(
        entries=[FillEntrySchema.from_dataclass(e) for e in entries]
    )


@router.post("/fill-entries/process", response_model=ProcessFillEntriesResponse)
def api_process_fill_entries(req: ProcessFillEntriesRequest):
    from back.fill_processor import process_fill_entries

    compiled = re.compile(req.pattern)
    dataclass_entries = [e.to_dataclass() for e in req.entries]
    processed = process_fill_entries(
        dataclass_entries, req.context_dir, compiled, req.provider
    )
    return ProcessFillEntriesResponse(
        entries=[FillEntrySchema.from_dataclass(e) for e in processed]
    )


@router.post("/context/read", response_model=ContextResponse)
def api_read_context(req: ContextDirRequest):
    return ContextResponse(context=context_store.read(req.context_dir))


@router.post("/context/add", response_model=ContextResponse)
def api_add_context(req: ContextKeyValueRequest):
    data = context_store.read(req.context_dir)
    data[req.key] = req.value
    context_store.write(req.context_dir, data)
    return ContextResponse(context=data)


@router.post("/context/update", response_model=ContextResponse)
def api_update_context(req: ContextKeyValueRequest):
    data = context_store.read(req.context_dir)
    if req.key in data:
        data[req.key] = req.value
        context_store.write(req.context_dir, data)
    return ContextResponse(context=data)


@router.post("/context/delete", response_model=ContextResponse)
def api_delete_context(req: ContextKeyRequest):
    data = context_store.read(req.context_dir)
    if req.key in data:
        del data[req.key]
        context_store.write(req.context_dir, data)
    return ContextResponse(context=data)


@router.post("/context/extract", response_model=ContextResponse)
def api_extract_context(req: ExtractContextRequest):
    from back.context_extractor import extract_context

    data = extract_context(req.context_dir, req.provider)
    context_store.write(req.context_dir, data)
    return ContextResponse(context=data)


@router.post("/checkbox-entries/detect", response_model=DetectCheckboxEntriesResponse)
def api_detect_checkbox_entries(req: DetectCheckboxEntriesRequest):
    from back.checkbox_processor import detect_checkbox_entries

    entries = detect_checkbox_entries(req.lines, req.keys)
    return DetectCheckboxEntriesResponse(
        entries=[CheckboxEntrySchema.from_dataclass(e) for e in entries]
    )


@router.post("/checkbox-entries/process", response_model=ProcessCheckboxEntriesResponse)
def api_process_checkbox_entries(req: ProcessCheckboxEntriesRequest):
    from back.checkbox_processor import process_checkbox_entries

    dataclass_entries = [e.to_dataclass() for e in req.entries]
    processed = process_checkbox_entries(
        dataclass_entries, req.context_dir, req.keys, req.provider
    )
    return ProcessCheckboxEntriesResponse(
        entries=[CheckboxEntrySchema.from_dataclass(e) for e in processed]
    )


@router.post("/docx/fill", response_model=FillFormResponse)
def api_fill_docx(req: FillDocxRequest):
    from back.docx_filler import fill_docx_with_entries

    dataclass_entries = [e.to_dataclass() for e in req.fill_entries]
    dataclass_checkboxes = [c.to_dataclass() for c in req.checkbox_entries]
    out_path = fill_docx_with_entries(
        dataclass_entries, dataclass_checkboxes, req.form_path, req.output_path
    )
    return FillFormResponse(output_path=out_path)


@router.post("/pdf/fill", response_model=FillFormResponse)
def api_fill_pdf(req: FillPdfRequest):
    from back.pdf_filler import fill_pdf_with_entries

    dataclass_entries = [e.to_dataclass() for e in req.fill_entries]
    dataclass_checkboxes = [c.to_dataclass() for c in req.checkbox_entries]
    out_path = fill_pdf_with_entries(
        dataclass_entries, dataclass_checkboxes, req.form_path, req.output_path
    )
    return FillFormResponse(output_path=out_path)
