from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional, Tuple, Literal
import re
import os
import json
import requests
from fastapi.middleware.cors import CORSMiddleware

from .text_extraction import extract_form_text
from .pattern_detection import detect_placeholder_patterns
from .fill_processor import detect_fill_entries, process_fill_entries, FillEntry
from .context_extractor import extract_context
from .docx_filler import fill_docx_with_entries
from .pdf_filler import fill_pdf_with_entries

app = FastAPI(title="EasyForm Backend API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend origin
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)
# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------


class FillEntrySchema(BaseModel):
    lines: str
    number_of_fill_spots: int
    context_keys: List[Optional[str]]
    filled_lines: str = ""

    @classmethod
    def from_dataclass(cls, entry: FillEntry) -> "FillEntrySchema":
        return cls(
            lines=entry.lines,
            number_of_fill_spots=entry.number_of_fill_spots,
            context_keys=entry.context_keys,
            filled_lines=entry.filled_lines,
        )

    def to_dataclass(self) -> FillEntry:
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
    def from_dataclass(cls, entry: "CheckboxEntry") -> "CheckboxEntrySchema":
        return cls(
            lines=entry.lines,
            checkbox_positions=entry.checkbox_positions,
            checkbox_values=entry.checkbox_values,
            context_key=entry.context_key,
            checked_indices=entry.checked_indices or [],
        )

    def to_dataclass(self) -> "CheckboxEntry":
        from .checkbox_processor import (
            CheckboxEntry,
        )  # local import to avoid circular dependency

        return CheckboxEntry(
            lines=self.lines,
            checkbox_positions=self.checkbox_positions,
            checkbox_values=self.checkbox_values,
            context_key=self.context_key,
            checked_indices=self.checked_indices,
        )


class FillDocxRequest(BaseModel):
    """Request payload for /docx/fill endpoint. All placeholder detection must have been done client-side.
    We simply receive the pre-computed fill entries and checkbox entries along with paths.
    """

    fill_entries: List[FillEntrySchema]
    checkbox_entries: List[CheckboxEntrySchema]
    form_path: str
    output_path: Optional[str] = None


class FillDocxResponse(BaseModel):
    output_path: str


class FillPdfRequest(BaseModel):
    fill_entries: List[FillEntrySchema]
    checkbox_entries: List[CheckboxEntrySchema] = (
        []
    )  # Currently ignored but accepted for symmetry
    form_path: str
    output_path: Optional[str] = None


class FillPdfResponse(BaseModel):
    output_path: str


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------


class ExtractFormTextRequest(BaseModel):
    form_path: str


class ExtractFormTextResponse(BaseModel):
    text: str


class DetectPatternRequest(BaseModel):
    text: str
    provider: Literal["openai", "groq", "anythingllm", "local"] 


class DetectPatternResponse(BaseModel):
    pattern: str  # regex pattern string


class DetectFillEntriesRequest(BaseModel):
    lines: List[str]
    keys: List[str]
    pattern: str  # regex pattern string
    provider: Literal["openai", "groq", "anythingllm", "local"]


class DetectFillEntriesResponse(BaseModel):
    entries: List[FillEntrySchema]


class ProcessFillEntriesRequest(BaseModel):
    entries: List[FillEntrySchema]
    context_dir: str
    pattern: str
    provider: Literal["openai", "groq", "anythingllm", "local"]


class ProcessFillEntriesResponse(BaseModel):
    entries: List[FillEntrySchema]


class ReadContextRequest(BaseModel):
    context_dir: str


class ReadContextResponse(BaseModel):
    context: dict


class UpdateContextRequest(BaseModel):
    context_dir: str
    key: str
    value: str


class UpdateContextResponse(BaseModel):
    context: dict


class AddContextRequest(BaseModel):
    context_dir: str
    key: str
    value: str


class AddContextResponse(BaseModel):
    context: dict


class DeleteContextRequest(BaseModel):
    context_dir: str
    key: str


class DeleteContextResponse(BaseModel):
    context: dict


class DetectCheckboxEntriesRequest(BaseModel):
    lines: List[str]
    keys: List[str]


class DetectCheckboxEntriesResponse(BaseModel):
    entries: List[CheckboxEntrySchema]


class ProcessCheckboxEntriesRequest(BaseModel):
    entries: List[CheckboxEntrySchema]
    context_dir: str
    keys: List[str]
    provider: Literal["openai", "groq", "anythingllm", "local"]


class ProcessCheckboxEntriesResponse(BaseModel):
    entries: List[CheckboxEntrySchema]


class ExtractContextRequest(BaseModel):
    context_dir: str
    provider: Literal["openai", "groq", "anythingllm", "local"]


class ExtractContextResponse(BaseModel):
    context: dict


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _context_path(context_dir: str) -> str:
    return os.path.join(context_dir, "context_data.json")


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------


@app.post("/form/text", response_model=ExtractFormTextResponse)
def api_extract_form_text(req: ExtractFormTextRequest):
    text = extract_form_text(req.form_path)
    return ExtractFormTextResponse(text=text)


@app.post("/pattern/detect", response_model=DetectPatternResponse)
def api_detect_pattern(req: DetectPatternRequest):
    pattern = detect_placeholder_patterns(req.text, req.provider)
    return DetectPatternResponse(pattern=pattern.pattern)


@app.post("/fill-entries/detect", response_model=DetectFillEntriesResponse)
def api_detect_fill_entries(req: DetectFillEntriesRequest):
    compiled = re.compile(req.pattern)
    entries = detect_fill_entries(req.lines, req.keys, compiled, req.provider)
    entries_schema = [FillEntrySchema.from_dataclass(e) for e in entries]
    return DetectFillEntriesResponse(entries=entries_schema)


@app.post("/fill-entries/process", response_model=ProcessFillEntriesResponse)
def api_process_fill_entries(req: ProcessFillEntriesRequest):
    compiled = re.compile(req.pattern)
    dataclass_entries = [e.to_dataclass() for e in req.entries]
    processed_entries = process_fill_entries(
        dataclass_entries, req.context_dir, compiled, req.provider
    )
    processed_schema = [FillEntrySchema.from_dataclass(e) for e in processed_entries]
    return ProcessFillEntriesResponse(entries=processed_schema)


@app.post("/context/read", response_model=ReadContextResponse)
def api_read_context(req: ReadContextRequest):
    path = _context_path(req.context_dir)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}
    return ReadContextResponse(context=data)


@app.post("/context/add", response_model=AddContextResponse)
def api_add_context(req: AddContextRequest):
    path = _context_path(req.context_dir)
    data = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    # Update and persist
    data[req.key] = req.value
    os.makedirs(req.context_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return AddContextResponse(context=data)


@app.post("/context/update", response_model=UpdateContextResponse)
def api_update_context(req: UpdateContextRequest):
    """Update a single key-value pair in the context data JSON file."""
    path = _context_path(req.context_dir)
    data = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    # Update and persist
    if req.key in data:
        data[req.key] = req.value

        os.makedirs(req.context_dir, exist_ok=True)
        with open(_context_path(req.context_dir), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    return UpdateContextResponse(context=data)


@app.post("/context/delete", response_model=DeleteContextResponse)
def api_delete_context(req: DeleteContextRequest):
    """Delete a key from the context data JSON file."""
    path = _context_path(req.context_dir)
    data = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    # Remove the key if it exists
    if req.key in data:
        del data[req.key]
    # Persist the updated context
    os.makedirs(req.context_dir, exist_ok=True)
    with open(_context_path(req.context_dir), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return DeleteContextResponse(context=data)


@app.post("/checkbox-entries/detect", response_model=DetectCheckboxEntriesResponse)
def api_detect_checkbox_entries(req: DetectCheckboxEntriesRequest):
    from .checkbox_processor import (
        detect_checkbox_entries,
    )  # local import to avoid heavy import at startup

    entries = detect_checkbox_entries(req.lines, req.keys)
    entries_schema = [CheckboxEntrySchema.from_dataclass(e) for e in entries]
    return DetectCheckboxEntriesResponse(entries=entries_schema)


@app.post("/checkbox-entries/process", response_model=ProcessCheckboxEntriesResponse)
def api_process_checkbox_entries(req: ProcessCheckboxEntriesRequest):
    from .checkbox_processor import (
        process_checkbox_entries,
    )  # local import to avoid heavy import at startup

    dataclass_entries = [e.to_dataclass() for e in req.entries]
    processed_entries = process_checkbox_entries(
        dataclass_entries, req.context_dir, req.keys, req.provider
    )
    processed_schema = [
        CheckboxEntrySchema.from_dataclass(e) for e in processed_entries
    ]
    return ProcessCheckboxEntriesResponse(entries=processed_schema)


@app.post("/context/extract", response_model=ExtractContextResponse)
def api_extract_context(req: ExtractContextRequest):
    # Extract context data from the provided directory and persist it to context_data.json
    data = extract_context(req.context_dir, req.provider)
    os.makedirs(req.context_dir, exist_ok=True)
    with open(_context_path(req.context_dir), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return ExtractContextResponse(context=data)


@app.post(
    "/docx/fill",
    response_model=FillDocxResponse,
    summary="Fill a DOCX form using pre-computed placeholder & checkbox entries",
    description=(
        "Takes the raw `form_path` to a DOCX template, a list of pre-processed `FillEntry` objects\n"
        "(each with its `filled_lines` already populated) and `CheckboxEntry` objects indicating which\n"
        "checkbox indices should be checked. No placeholder or checkbox pattern detection is executed\n"
        "server-side — the entries must be prepared on the client. The filled document is written to\n"
        "`output_path` (or '<form>_filled.docx' beside the original) and the absolute path is returned."
    ),
)
def api_fill_docx(req: FillDocxRequest):
    dataclass_entries = [e.to_dataclass() for e in req.fill_entries]
    dataclass_checkboxes = [c.to_dataclass() for c in req.checkbox_entries]
    out_path = fill_docx_with_entries(
        dataclass_entries, dataclass_checkboxes, req.form_path, req.output_path
    )
    return FillDocxResponse(output_path=out_path)


@app.post(
    "/pdf/fill",
    response_model=FillPdfResponse,
    summary="Fill a PDF form using pre-computed placeholder & checkbox entries",
    description=(
        "Similar to `/docx/fill` but for PDF files. Interactive AcroForm fields are attempted first; if the\n"
        "PDF is flat, text overlay is used. Checkbox entries are currently ignored (no overlay support yet)\n"
        "but accepted for forward compatibility. Output path mirrors DOCX behaviour."
    ),
)
def api_fill_pdf(req: FillPdfRequest):
    dataclass_entries = [e.to_dataclass() for e in req.fill_entries]
    dataclass_checkboxes = [c.to_dataclass() for c in req.checkbox_entries]
    out_path = fill_pdf_with_entries(
        dataclass_entries, dataclass_checkboxes, req.form_path, req.output_path
    )
    return FillPdfResponse(output_path=out_path)


@app.get("/health")
def health_check():
    return {"status": "ok"}
