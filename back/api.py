from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional, Tuple
import re
import os
import json

from .text_extraction import extract_form_text
from .pattern_detection import detect_placeholder_patterns
from .fill_processor import detect_fill_entries, process_fill_entries, FillEntry
from .context_extractor import extract_context

app = FastAPI(title="EasyForm Backend API", version="0.1.0")

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
        from .checkbox_processor import CheckboxEntry  # local import to avoid circular dependency
        return CheckboxEntry(
            lines=self.lines,
            checkbox_positions=self.checkbox_positions,
            checkbox_values=self.checkbox_values,
            context_key=self.context_key,
            checked_indices=self.checked_indices,
        )

# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------

class ExtractFormTextRequest(BaseModel):
    form_path: str

class ExtractFormTextResponse(BaseModel):
    text: str

class DetectPatternRequest(BaseModel):
    text: str

class DetectPatternResponse(BaseModel):
    pattern: str  # regex pattern string

class DetectFillEntriesRequest(BaseModel):
    lines: List[str]
    keys: List[str]
    pattern: str  # regex pattern string

class DetectFillEntriesResponse(BaseModel):
    entries: List[FillEntrySchema]

class ProcessFillEntriesRequest(BaseModel):
    entries: List[FillEntrySchema]
    context_dir: str
    pattern: str

class ProcessFillEntriesResponse(BaseModel):
    entries: List[FillEntrySchema]

class ReadContextRequest(BaseModel):
    context_dir: str

class ReadContextResponse(BaseModel):
    context: dict

class AddContextRequest(BaseModel):
    context_dir: str
    key: str
    value: str

class AddContextResponse(BaseModel):
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

class ProcessCheckboxEntriesResponse(BaseModel):
    entries: List[CheckboxEntrySchema]

class ExtractContextRequest(BaseModel):
    context_dir: str

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
    pattern = detect_placeholder_patterns(req.text)
    return DetectPatternResponse(pattern=pattern.pattern)


@app.post("/fill-entries/detect", response_model=DetectFillEntriesResponse)
def api_detect_fill_entries(req: DetectFillEntriesRequest):
    compiled = re.compile(req.pattern)
    entries = detect_fill_entries(req.lines, req.keys, compiled)
    entries_schema = [FillEntrySchema.from_dataclass(e) for e in entries]
    return DetectFillEntriesResponse(entries=entries_schema)


@app.post("/fill-entries/process", response_model=ProcessFillEntriesResponse)
def api_process_fill_entries(req: ProcessFillEntriesRequest):
    compiled = re.compile(req.pattern)
    dataclass_entries = [e.to_dataclass() for e in req.entries]
    processed_entries = process_fill_entries(dataclass_entries, req.context_dir, compiled)
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


@app.post("/checkbox-entries/detect", response_model=DetectCheckboxEntriesResponse)
def api_detect_checkbox_entries(req: DetectCheckboxEntriesRequest):
    from .checkbox_processor import detect_checkbox_entries  # local import to avoid heavy import at startup
    entries = detect_checkbox_entries(req.lines, req.keys)
    entries_schema = [CheckboxEntrySchema.from_dataclass(e) for e in entries]
    return DetectCheckboxEntriesResponse(entries=entries_schema)


@app.post("/checkbox-entries/process", response_model=ProcessCheckboxEntriesResponse)
def api_process_checkbox_entries(req: ProcessCheckboxEntriesRequest):
    from .checkbox_processor import process_checkbox_entries  # local import to avoid heavy import at startup
    dataclass_entries = [e.to_dataclass() for e in req.entries]
    processed_entries = process_checkbox_entries(dataclass_entries, req.context_dir, req.keys)
    processed_schema = [CheckboxEntrySchema.from_dataclass(e) for e in processed_entries]
    return ProcessCheckboxEntriesResponse(entries=processed_schema)


@app.post("/context/extract", response_model=ExtractContextResponse)
def api_extract_context(req: ExtractContextRequest):
    # Extract context data from the provided directory and persist it to context_data.json
    data = extract_context(req.context_dir)
    os.makedirs(req.context_dir, exist_ok=True)
    with open(_context_path(req.context_dir), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return ExtractContextResponse(context=data)


@app.get("/health")
def health_check():
    return {"status": "ok"} 