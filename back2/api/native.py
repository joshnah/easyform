"""Native (document-first) API routes.

These are the recommended endpoints. They drive the `back2.pipeline` phases
directly and have no dependency on the legacy `back/` package.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from back2.fillers import get_filler_for_extension
from back2.pipeline import ContextSearcher, DocumentAnalyzer, DocumentFirstWorkflow
from back2.providers import ProviderType, get_available_providers
from back2.schemas import FieldRequirement

router = APIRouter()


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


@router.get("/health")
async def health_check():
    return {"status": "ok", "workflow": "document-first"}


@router.get("/providers")
async def list_providers():
    return {"providers": get_available_providers()}


@router.post("/document/analyze")
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


@router.post("/context/search")
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


@router.post("/document/fill")
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
        )

    return {
        "saved": request.save,
        "output_path": output_path,
        "fill_result": None if request.save else fill_result,
    }


@router.post("/process")
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


@router.get("/context/list")
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


@router.get("/document/info")
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
