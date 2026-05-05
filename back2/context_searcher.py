"""Search a context directory for values matching field requirements."""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from back2.json_utils import parse_json_response
from back2.prompts import context_search_prompt
from back2.providers import get_provider
from back2.schemas import FieldRequirement
from back2.text_extraction import extract_text_from_file
from back2.text_splitter import split_text
from back2.tokenization import count_tokens

CONTEXT_WINDOW = 4090
TOKENS_FOR_OUTPUT = 400  # reserved for the model's reply
BATCH_SIZE = 10  # field keys per LLM call
SUPPORTED_EXTS = {".txt", ".md", ".json", ".pdf", ".docx"}

# `count_tokens` reports tokens; `split_text` works in characters. Use the
# heuristic 1 token ≈ 4 chars so the token-budget guides the char-based split.
CHARS_PER_TOKEN = 4


class ContextSearcher:
    """Searches a context directory for values needed by document fields."""

    def __init__(self, provider: str = "groq"):
        self.provider = provider
        self._llm = get_provider(provider)

    def search_context(
        self, field_requirements: List[FieldRequirement], context_dir: str
    ) -> List[FieldRequirement]:
        """
        Populate `.value` (and `.context_key`) on each FieldRequirement based on
        what we find in the context directory. Also writes the discovered
        key→value map to `context_data.json` in the directory.
        """
        context_files = self._scan_context_directory(context_dir)
        all_context_text = self._extract_all_context_text(context_files)

        # Pre-compute the prompt overhead by formatting an empty prompt once.
        merged_chunks = self._process_and_split_context(
            all_context_text, context_search_prompt([], [], "")
        )

        context_data: Dict[str, Optional[str]] = {}
        for i in range(0, len(field_requirements), BATCH_SIZE):
            batch = field_requirements[i : i + BATCH_SIZE]
            keys = [f.context_key for f in batch]
            types = [f.field_type for f in batch]

            found = self._search_for_keys(keys, types, merged_chunks)
            context_data.update(found)

            for f in batch:
                if f.context_key in found:
                    f.value = found[f.context_key]

        output_file = os.path.join(context_dir, "context_data.json")
        with open(output_file, "w", encoding="utf-8") as fh:
            json.dump(context_data, fh, indent=2, ensure_ascii=False)

        return field_requirements

    def _scan_context_directory(self, context_dir: str) -> List[str]:
        """Return readable context files, skipping our own context_data.json."""
        files: List[str] = []
        for root, _, names in os.walk(context_dir):
            for name in names:
                if name == "context_data.json":
                    continue
                if Path(name).suffix.lower() in SUPPORTED_EXTS:
                    files.append(os.path.join(root, name))
        return files

    def _extract_all_context_text(self, context_files: List[str]) -> List[str]:
        """Extract one labelled text block per context file (skip on failure)."""
        blocks: List[str] = []
        for path in context_files:
            try:
                text = extract_text_from_file(path)
            except Exception as e:
                print(f"Skipping {path}: {e}")
                continue
            if text:
                blocks.append(f"\n\n=== {os.path.basename(path)} ===\n{text}")
        return blocks

    def _search_for_keys(
        self,
        context_keys: List[str],
        field_types: List[str],
        chunks: List[str],
    ) -> Dict[str, Optional[str]]:
        """
        Walk through context chunks and return {key: value} for the keys we
        could resolve. Stops early once every key has a value.
        """
        results: Dict[str, Optional[str]] = {k: None for k in context_keys}

        for text in chunks:
            prompt = context_search_prompt(context_keys, field_types, text)
            try:
                response = self._llm.query_gpt(
                    prompt, max_tokens=1000, temperature=0.1
                ).strip()
            except Exception as e:
                print(f"LLM query failed in context search: {e}")
                continue

            parsed = parse_json_response(response)
            self._merge_response_into_results(parsed, context_keys, results)

            if all(v is not None for v in results.values()):
                break

        return results

    @staticmethod
    def _merge_response_into_results(
        parsed,
        context_keys: List[str],
        results: Dict[str, Optional[str]],
    ) -> None:
        """Fold one LLM response (already JSON-parsed) into the running results."""
        if isinstance(parsed, dict):
            parsed = [parsed]
        if not isinstance(parsed, list):
            return

        for idx, item in enumerate(parsed):
            if not isinstance(item, dict):
                continue
            key = item.get("context_key") or item.get("key") or item.get("contextKey")
            if key is None and idx < len(context_keys):
                key = context_keys[idx]
            if key not in results or results[key] is not None:
                continue

            value = item.get("value", item.get("val"))
            if isinstance(value, str):
                value = value.strip()
                if value.lower() in ("null", "none", ""):
                    value = None
            results[key] = value

    def _process_and_split_context(
        self, all_text: List[str], placeholder_prompt: str
    ) -> List[str]:
        """
        Split each text block to fit a single LLM call (after accounting for
        prompt overhead and reserved output), then greedily merge the resulting
        sub-chunks. Token counts are computed once per chunk and reused.
        """
        prompt_tokens = count_tokens(placeholder_prompt)
        budget_tokens = CONTEXT_WINDOW - prompt_tokens - TOKENS_FOR_OUTPUT
        budget_chars = max(1, budget_tokens * CHARS_PER_TOKEN)

        chunk_token_counts: List[Tuple[str, int]] = []
        for chunk in all_text:
            tokens = count_tokens(chunk)
            if tokens <= budget_tokens:
                chunk_token_counts.append((chunk, tokens))
                continue

            for sub in split_text(chunk, chunk_size=budget_chars, chunk_overlap=50):
                chunk_token_counts.append((sub, count_tokens(sub)))

        # Pack small chunks together (smallest first) for fewer LLM calls.
        chunk_token_counts.sort(key=lambda x: x[1])

        merged: List[str] = []
        current_text = ""
        current_tokens = 0
        for text, tokens in chunk_token_counts:
            if current_text and current_tokens + tokens > budget_tokens:
                merged.append(current_text)
                current_text = text
                current_tokens = tokens
            else:
                current_text = current_text + text if current_text else text
                current_tokens += tokens
        if current_text:
            merged.append(current_text)

        return merged
