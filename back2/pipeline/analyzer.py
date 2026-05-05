"""Analyze a document to identify fillable fields and their requirements."""

import re
from typing import Dict, List, Optional, Tuple

from back2.extraction.patterns import detect_placeholder_pattern
from back2.extraction.text import extract_text_from_file
from back2.pipeline.prompts import field_analysis_prompt
from back2.providers import get_provider
from back2.schemas import FieldRequirement
from back2.utils.json_parser import parse_json_response
from back2.utils.tokenization import count_tokens

CONTEXT_WINDOW = 4090
PROMPT_OVERHEAD = 128
TOKENS_PER_FIELD_OUTPUT = 10
SURROUNDING_LINES = 3  # lines before/after each placeholder line for context


class DocumentAnalyzer:
    """Identifies what information needs to be filled in a document."""

    def __init__(self, provider: str = "groq"):
        self.provider = provider
        self._llm = get_provider(provider)

    def analyze_document(
        self, document_path: str
    ) -> Tuple[List[FieldRequirement], Dict]:
        """
        Run extract → detect-pattern → find-fields → infer-types-and-keys.

        Returns the populated field list and a metadata dict (text, lines, pattern).
        """
        document_text = extract_text_from_file(document_path)
        lines = document_text.split("\n")

        placeholder_pattern = detect_placeholder_pattern(document_text)
        pattern_regex = re.compile(placeholder_pattern)

        found_fields = self._find_placeholder_fields(
            lines, pattern_regex, placeholder_pattern
        )
        batches = self._batch_fields_for_llm(found_fields)

        field_requirements: List[FieldRequirement] = []
        for batch in batches:
            field_requirements.extend(self._analyze_batch(batch))

        metadata = {
            "document_path": document_path,
            "document_text": document_text,
            "lines": lines,
            "placeholder_pattern": placeholder_pattern,
            "total_fields": len(field_requirements),
        }
        return field_requirements, metadata

    @staticmethod
    def _find_placeholder_fields(
        lines: List[str], pattern_regex: re.Pattern, placeholder_pattern: str
    ) -> List[FieldRequirement]:
        """Walk lines and emit one FieldRequirement per placeholder match."""
        fields: List[FieldRequirement] = []
        counter = 0
        for line_num, line in enumerate(lines):
            if not pattern_regex.search(line):
                continue
            start = max(0, line_num - SURROUNDING_LINES)
            end = min(len(lines), line_num + SURROUNDING_LINES + 1)
            surrounding = "\n".join(lines[start:end])

            for match in pattern_regex.finditer(line):
                counter += 1
                fields.append(
                    FieldRequirement(
                        field_id=f"field_{counter:03d}",
                        field_text=line.strip(),
                        line_number=line_num + 1,
                        match_position=match.start(),
                        surrounding_context=surrounding,
                        placeholder_pattern=placeholder_pattern,
                    )
                )
        return fields

    @staticmethod
    def _batch_fields_for_llm(
        found_fields: List[FieldRequirement],
    ) -> List[List[FieldRequirement]]:
        """
        Greedy-pack fields into batches that fit the model context window.
        Fields larger than the per-batch budget are dropped (logged).
        """
        if not found_fields:
            return []

        per_field_cap = CONTEXT_WINDOW - PROMPT_OVERHEAD - TOKENS_PER_FIELD_OUTPUT

        sized: List[Tuple[FieldRequirement, int]] = []
        for f in found_fields:
            combined = (f.field_text or "") + "\n" + (f.surrounding_context or "")
            count = count_tokens(combined)
            if count <= per_field_cap:
                sized.append((f, count))
            else:
                print(f"Skipping {f.field_id}: token count {count} exceeds cap {per_field_cap}")

        batches: List[List[FieldRequirement]] = []
        current: List[FieldRequirement] = []
        current_tokens = 0
        for f, count in sized:
            prospective = len(current) + 1
            allowance = (
                CONTEXT_WINDOW - PROMPT_OVERHEAD - TOKENS_PER_FIELD_OUTPUT * prospective
            )
            if current and current_tokens + count > allowance:
                batches.append(current)
                current = [f]
                current_tokens = count
            else:
                current.append(f)
                current_tokens += count
        if current:
            batches.append(current)
        return batches

    def _analyze_batch(
        self, fields: List[FieldRequirement]
    ) -> List[FieldRequirement]:
        """Run one batched LLM call to assign field_type + context_key."""
        types, keys = self._infer_types_and_keys(
            [(f.field_text, f.surrounding_context) for f in fields]
        )

        results: List[FieldRequirement] = []
        for f, ftype, key in zip(fields, types, keys):
            results.append(
                FieldRequirement(
                    field_id=f.field_id,
                    field_text=f.field_text.strip(),
                    field_type=ftype,
                    context_key=key,
                    line_number=f.line_number,
                    placeholder_pattern=f.placeholder_pattern,
                    surrounding_context=f.surrounding_context,
                )
            )
        return results

    def _infer_types_and_keys(
        self, fields: List[Tuple[str, str]]
    ) -> Tuple[List[str], List[Optional[str]]]:
        """
        One LLM call returning (field_types, context_keys) for the batch.
        Pads with defaults if the model returns too few items, truncates if too many.
        """
        prompt = field_analysis_prompt(fields)
        try:
            raw = self._llm.query_gpt(prompt, max_tokens=1000, temperature=0.1).strip()
        except Exception as e:
            print(f"LLM query failed in _infer_types_and_keys: {e}")
            return ["other"] * len(fields), [None] * len(fields)

        parsed = parse_json_response(raw)
        if isinstance(parsed, dict):
            parsed = [parsed]
        items = parsed if isinstance(parsed, list) else []

        types: List[str] = []
        keys: List[Optional[str]] = []
        for item in items:
            if not isinstance(item, dict):
                types.append("other")
                keys.append(None)
                continue
            ftype = (
                item.get("field_type")
                or item.get("type")
                or item.get("fieldType")
                or item.get("field")
                or "other"
            )
            key = (
                item.get("key")
                or item.get("suggested_contextKey")
                or item.get("suggested_context_key")
                or item.get("context_key")
                or item.get("contextKey")
            )
            types.append(ftype.strip() if isinstance(ftype, str) else "other")
            keys.append(key.strip() if isinstance(key, str) else None)

        if len(types) < len(fields):
            deficit = len(fields) - len(types)
            types.extend(["other"] * deficit)
            keys.extend([None] * deficit)
        elif len(types) > len(fields):
            types = types[: len(fields)]
            keys = keys[: len(fields)]

        return types, keys
