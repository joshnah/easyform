"""Main workflow orchestrator for the back2 document-first approach."""

from pathlib import Path
from typing import Dict, Optional

from back2.fillers import get_filler_for_extension
from back2.pipeline.analyzer import DocumentAnalyzer
from back2.pipeline.searcher import ContextSearcher


class DocumentFirstWorkflow:
    """
    Three-phase pipeline:
        1. Analyze the document → list of FieldRequirements.
        2. Search the context dir → fill `.value` on each requirement.
        3. Fill the document and save it.
    """

    def __init__(self, provider: str = "groq"):
        self.provider = provider
        self.document_analyzer = DocumentAnalyzer(provider)
        self.context_searcher = ContextSearcher(provider)

    def process_document(
        self, document_path: str, context_dir: str, output_path: Optional[str] = None
    ) -> Dict:
        # Phase 1: analyze
        field_requirements, doc_metadata = self.document_analyzer.analyze_document(
            document_path
        )

        # Phase 2: search context (mutates field_requirements with .value)
        self.context_searcher.search_context(field_requirements, context_dir)

        # Phase 3: fill + save
        ext = Path(document_path).suffix.lower().lstrip(".") or "txt"
        form_filler = get_filler_for_extension(ext)
        fill_result = form_filler.fill_form(
            document_text=doc_metadata["document_text"],
            field_requirements=field_requirements,
        )

        if output_path is None:
            input_path = Path(document_path)
            output_path = str(
                input_path.parent / f"{input_path.stem}_filled{input_path.suffix}"
            )
        form_filler.save_filled_document(fill_result, output_path, extension=ext)

        return self._build_summary(
            document_path=document_path,
            output_path=output_path,
            context_dir=context_dir,
            field_requirements=field_requirements,
            fill_result=fill_result,
        )

    @staticmethod
    def _build_summary(
        document_path, output_path, context_dir, field_requirements, fill_result
    ) -> Dict:
        required_keys = {r.context_key for r in field_requirements if r.context_key}
        found_keys = {r.context_key for r in field_requirements if r.value}
        return {
            "workflow": "document-first",
            "input_document": document_path,
            "output_document": output_path,
            "context_directory": context_dir,
            "analysis": {
                "total_fields_found": len(field_requirements),
                "field_types": sorted({r.field_type for r in field_requirements if r.field_type}),
                "required_context_keys": sorted(required_keys),
            },
            "context_search": {
                "keys_searched": len(required_keys),
                "values_found": len(found_keys),
                "found_keys": sorted(found_keys),
                "missing_keys": sorted(required_keys - found_keys),
            },
            "filling": {
                "fields_filled": len(fill_result.filled_fields),
                "fields_unfilled": len(fill_result.unfilled_fields),
                "success": fill_result.success,
                "filled_field_ids": fill_result.filled_fields,
                "unfilled_field_ids": fill_result.unfilled_fields,
            },
        }


def main_workflow(
    document_path: str,
    context_dir: str,
    output_path: Optional[str] = None,
    provider: str = "groq",
) -> Dict:
    """Top-level entry point used by the CLI."""
    return DocumentFirstWorkflow(provider).process_document(
        document_path, context_dir, output_path
    )
