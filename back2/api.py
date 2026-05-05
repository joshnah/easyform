"""FastAPI server for the back2 backend.

Exposes two endpoint surfaces on the same app:

1. Native back2 (document-first) endpoints — analyze / search / fill / process.
2. Legacy compatibility endpoints used by the existing frontend and root
   test scripts (form/text, pattern/detect, fill-entries/*, context/*,
   pdf/fill, docx/fill). These delegate into the legacy `back` package so
   filling behavior (PDF overlay, DOCX placeholder replacement) is preserved.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from back2.context_searcher import ContextSearcher
from back2.document_analyzer import DocumentAnalyzer
from back2.form_fillers import get_filler_for_extension
from back2.providers import ProviderType, get_available_providers
from back2.schemas import FieldRequirement
from back2.workflow import DocumentFirstWorkflow

app = FastAPI(title="EasyForm Backend API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Native back2 (document-first) endpoints
# ---------------------------------------------------------------------------


class AnalyzeDocumentRequest(BaseModel):
    document_path: str
    provider: ProviderType = "groq"


class SearchContextRequest(BaseModel):
    field_requirements: List[Dict]
    context_dir: str
    provider: ProviderType = "groq"


class FillDocumentRequest(BaseModel):
    document_path: str
    document_text: str
    field_requirements: List[Dict]
    save: bool = False
    output_path: Optional[str] = None
    extension: Optional[str] = None


class ProcessDocumentRequest(BaseModel):
    document_path: str
    context_dir: str
    output_path: Optional[str] = None
    provider: ProviderType = "groq"


@app.get("/health")
async def health_check():
    return {"status": "ok", "workflow": "document-first"}


@app.get("/providers")
async def list_providers():
    return {"providers": get_available_providers()}


@app.post("/document/analyze")
async def analyze_document(request: AnalyzeDocumentRequest):
    if not os.path.exists(request.document_path):
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        analyzer = DocumentAnalyzer(request.provider)
        field_requirements, metadata = analyzer.analyze_document(request.document_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document analysis failed: {e}")

    return {
        "field_requirements": field_requirements,
        "metadata": {
            "document_text": metadata["document_text"],
            "total_fields": len(field_requirements),
            "placeholder_pattern": metadata["placeholder_pattern"],
            "document_path": request.document_path,
        },
    }


@app.post("/context/search")
async def search_context(request: SearchContextRequest):
    if not os.path.exists(request.context_dir):
        raise HTTPException(status_code=404, detail="Context directory not found")

    try:
        field_requirements = [
            FieldRequirement(**req) for req in request.field_requirements
        ]
        searcher = ContextSearcher(request.provider)
        field_requirements = searcher.search_context(
            field_requirements, request.context_dir
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Context search failed: {e}")

    return {"field_requirements": field_requirements}


@app.post("/document/fill")
async def fill_document(request: FillDocumentRequest):
    if not os.path.exists(request.document_path):
        raise HTTPException(status_code=404, detail="Document not found")

    extension = request.extension or Path(request.document_path).suffix.lstrip(".")
    form_filler = get_filler_for_extension(extension)

    try:
        field_requirements = [
            FieldRequirement(**req) for req in request.field_requirements
        ]
        fill_result = form_filler.fill_form(
            document_text=request.document_text,
            field_requirements=field_requirements,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document filling failed: {e}")

    output_path = None
    if request.save:
        suffix = Path(request.document_path).suffix
        output_path = request.output_path or request.document_path.replace(
            suffix, f".filled{suffix}"
        )
        form_filler.save_filled_document(
            fill_result=fill_result,
            output_path=output_path,
            extension=extension,
        )

    return {
        "saved": request.save,
        "output_path": output_path,
        "fill_result": None if request.save else fill_result,
    }


@app.post("/process")
async def process_document(request: ProcessDocumentRequest):
    if not os.path.exists(request.document_path):
        raise HTTPException(status_code=404, detail="Document not found")
    if not os.path.exists(request.context_dir):
        raise HTTPException(status_code=404, detail="Context directory not found")

    try:
        workflow = DocumentFirstWorkflow(provider=request.provider)
        return workflow.process_document(
            document_path=request.document_path,
            context_dir=request.context_dir,
            output_path=request.output_path,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")


@app.get("/context/list")
async def list_context_files(context_dir: str):
    if not os.path.exists(context_dir):
        raise HTTPException(status_code=404, detail="Context directory not found")

    files = []
    for root, _, filenames in os.walk(context_dir):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            files.append(
                {
                    "name": filename,
                    "path": file_path,
                    "size": os.path.getsize(file_path),
                    "extension": Path(filename).suffix.lower(),
                }
            )
    return {"files": files, "total": len(files)}


@app.get("/document/info")
async def get_document_info(document_path: str):
    if not os.path.exists(document_path):
        raise HTTPException(status_code=404, detail="Document not found")

    path_obj = Path(document_path)
    return {
        "name": path_obj.name,
        "path": document_path,
        "size": os.path.getsize(document_path),
        "extension": path_obj.suffix.lower(),
        "exists": True,
    }


# ---------------------------------------------------------------------------
# Legacy compatibility surface (frontend + root test scripts)
#
# These mirror the original back/api.py paths and schemas. They internally
# delegate to the legacy `back` package, which still owns the OCR + Docling
# context extraction and the PDF/DOCX overlay fill logic. Once those are
# ported into back2, the imports below can flip over.
# ---------------------------------------------------------------------------

LegacyProvider = Literal["openai", "groq", "anythingllm", "local"]


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


def _context_path(context_dir: str) -> str:
    return os.path.join(context_dir, "context_data.json")


def _read_context(context_dir: str) -> dict:
    path = _context_path(context_dir)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_context(context_dir: str, data: dict) -> None:
    os.makedirs(context_dir, exist_ok=True)
    with open(_context_path(context_dir), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


@app.post("/form/text", response_model=ExtractFormTextResponse)
def api_extract_form_text(req: ExtractFormTextRequest):
    from back.text_extraction import extract_form_text

    return ExtractFormTextResponse(text=extract_form_text(req.form_path))


@app.post("/pattern/detect", response_model=DetectPatternResponse)
def api_detect_pattern(req: DetectPatternRequest):
    from back.pattern_detection import detect_placeholder_patterns

    pattern = detect_placeholder_patterns(req.text, req.provider)
    return DetectPatternResponse(pattern=pattern.pattern)


@app.post("/fill-entries/detect", response_model=DetectFillEntriesResponse)
def api_detect_fill_entries(req: DetectFillEntriesRequest):
    from back.fill_processor import detect_fill_entries

    compiled = re.compile(req.pattern)
    entries = detect_fill_entries(req.lines, req.keys, compiled, req.provider)
    return DetectFillEntriesResponse(
        entries=[FillEntrySchema.from_dataclass(e) for e in entries]
    )


@app.post("/fill-entries/process", response_model=ProcessFillEntriesResponse)
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


@app.post("/context/read", response_model=ContextResponse)
def api_read_context(req: ContextDirRequest):
    return ContextResponse(context=_read_context(req.context_dir))


@app.post("/context/add", response_model=ContextResponse)
def api_add_context(req: ContextKeyValueRequest):
    data = _read_context(req.context_dir)
    data[req.key] = req.value
    _write_context(req.context_dir, data)
    return ContextResponse(context=data)


@app.post("/context/update", response_model=ContextResponse)
def api_update_context(req: ContextKeyValueRequest):
    data = _read_context(req.context_dir)
    if req.key in data:
        data[req.key] = req.value
        _write_context(req.context_dir, data)
    return ContextResponse(context=data)


@app.post("/context/delete", response_model=ContextResponse)
def api_delete_context(req: ContextKeyRequest):
    data = _read_context(req.context_dir)
    if req.key in data:
        del data[req.key]
        _write_context(req.context_dir, data)
    return ContextResponse(context=data)


@app.post("/context/extract", response_model=ContextResponse)
def api_extract_context(req: ExtractContextRequest):
    from back.context_extractor import extract_context

    data = extract_context(req.context_dir, req.provider)
    _write_context(req.context_dir, data)
    return ContextResponse(context=data)


@app.post("/checkbox-entries/detect", response_model=DetectCheckboxEntriesResponse)
def api_detect_checkbox_entries(req: DetectCheckboxEntriesRequest):
    from back.checkbox_processor import detect_checkbox_entries

    entries = detect_checkbox_entries(req.lines, req.keys)
    return DetectCheckboxEntriesResponse(
        entries=[CheckboxEntrySchema.from_dataclass(e) for e in entries]
    )


@app.post("/checkbox-entries/process", response_model=ProcessCheckboxEntriesResponse)
def api_process_checkbox_entries(req: ProcessCheckboxEntriesRequest):
    from back.checkbox_processor import process_checkbox_entries

    dataclass_entries = [e.to_dataclass() for e in req.entries]
    processed = process_checkbox_entries(
        dataclass_entries, req.context_dir, req.keys, req.provider
    )
    return ProcessCheckboxEntriesResponse(
        entries=[CheckboxEntrySchema.from_dataclass(e) for e in processed]
    )


@app.post("/docx/fill", response_model=FillFormResponse)
def api_fill_docx(req: FillDocxRequest):
    from back.docx_filler import fill_docx_with_entries

    dataclass_entries = [e.to_dataclass() for e in req.fill_entries]
    dataclass_checkboxes = [c.to_dataclass() for c in req.checkbox_entries]
    out_path = fill_docx_with_entries(
        dataclass_entries, dataclass_checkboxes, req.form_path, req.output_path
    )
    return FillFormResponse(output_path=out_path)


@app.post("/pdf/fill", response_model=FillFormResponse)
def api_fill_pdf(req: FillPdfRequest):
    from back.pdf_filler import fill_pdf_with_entries

    dataclass_entries = [e.to_dataclass() for e in req.fill_entries]
    dataclass_checkboxes = [c.to_dataclass() for c in req.checkbox_entries]
    out_path = fill_pdf_with_entries(
        dataclass_entries, dataclass_checkboxes, req.form_path, req.output_path
    )
    return FillFormResponse(output_path=out_path)
