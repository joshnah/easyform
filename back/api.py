from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import re
import os
import json

from .text_extraction import extract_form_text
from .pattern_detection import detect_placeholder_patterns
from .fill_processor import detect_fill_entries, process_fill_entries, FillEntry

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


@app.get("/health")
def health_check():
    return {"status": "ok"} 