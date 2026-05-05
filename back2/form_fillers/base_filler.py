"""Base form-filler: replaces placeholders in document text and saves the result."""

import json
import re
from dataclasses import dataclass
from typing import List, Optional

from back2.schemas import FieldRequirement


@dataclass
class FillResult:
    """Result of filling a document."""

    original_text: str
    filled_text: str
    filled_fields: List[str]
    unfilled_fields: List[str]
    success: bool


class BaseFiller:
    """Shared filling logic. Subclasses implement `_save` for their format."""

    def fill_form(
        self,
        document_text: str,
        field_requirements: List[FieldRequirement],
    ) -> FillResult:
        """Replace each requirement's placeholder with its `value` (if present)."""
        filled_text = document_text
        filled: List[str] = []
        unfilled: List[str] = []

        # Process line-by-line in document order so multi-placeholder lines
        # are handled deterministically.
        for req in sorted(field_requirements, key=lambda r: r.line_number):
            if not getattr(req, "value", None):
                unfilled.append(req.field_id)
                continue

            pattern_regex = re.compile(req.placeholder_pattern)
            updated = self._replace_field_in_text(
                filled_text, req, req.value, pattern_regex
            )
            if updated is None:
                unfilled.append(req.field_id)
            else:
                filled_text = updated
                filled.append(req.field_id)

        return FillResult(
            original_text=document_text,
            filled_text=filled_text,
            filled_fields=filled,
            unfilled_fields=unfilled,
            success=bool(filled),
        )

    @staticmethod
    def _replace_field_in_text(
        text: str,
        field_req: FieldRequirement,
        value: str,
        pattern_regex: re.Pattern,
    ) -> Optional[str]:
        """Replace the first placeholder on `field_req.line_number` with `value`."""
        lines = text.split("\n")
        idx = field_req.line_number - 1
        if idx >= len(lines):
            return None

        match = pattern_regex.search(lines[idx])
        if match is None:
            return None

        line = lines[idx]
        lines[idx] = line[: match.start()] + value + line[match.end() :]
        return "\n".join(lines)

    def _save(self, fill_result: FillResult, output_path: str) -> None:
        raise NotImplementedError("Subclasses must implement _save")

    def save_filled_document(
        self, fill_result: FillResult, output_path: str, extension: str = "txt"
    ) -> None:
        """Write the filled document plus a `<output>.metadata.json` sidecar."""
        if not isinstance(fill_result, FillResult):
            raise TypeError("save_filled_document expects a FillResult instance")

        output_path = output_path or f"output.{extension}"
        self._save(fill_result, output_path)

        metadata_path = output_path + ".metadata.json"
        metadata = {
            "filled_fields": fill_result.filled_fields,
            "unfilled_fields": fill_result.unfilled_fields,
            "success": fill_result.success,
            "total_fields": len(fill_result.filled_fields)
            + len(fill_result.unfilled_fields),
        }
        try:
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to write metadata file {metadata_path}: {e}")
