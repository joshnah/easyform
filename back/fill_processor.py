"""
Fill entry processing for form filling.

This module handles detection and processing of fill entries (placeholder fields)
in forms, including context key inference and value filling.
"""

import os
import re
import json
import logging
from typing import Literal
from dataclasses import dataclass
from typing import List, Optional, cast
from .context_extractor import extract_context
from .llm_client import query_gpt
from .prompts import (
    fill_entry_match_prompt,
    fill_entry_retry_prompt,
    missing_key_inference_prompt,
    context_value_search_prompt,
)


@dataclass
class FillEntry:
    lines: str
    number_of_fill_spots: int
    context_keys: List[Optional[str]]
    filled_lines: str = ""


# Heuristic keyword mapping to context keys. This is used as a fallback when the LLM
# cannot confidently map a placeholder to an existing key. The mapping should stay
# relatively small and generic so that it does not introduce incorrect matches.
# Extend this list over time as additional common placeholders are discovered.
COMMON_KEYWORD_MAPPING: dict[str, list[str]] = {
    # personal identity
    "name": ["full_name", "first_name", "last_name", "name"],
    "first name": ["first_name"],
    "last name": ["last_name"],
    # contact
    "phone": ["phone_number", "phone"],
    "telephone": ["phone_number", "phone"],
    "mobile": ["phone_number", "phone"],
    "email": ["email", "email_address"],
    "e-mail": ["email", "email_address"],
    "address": ["address", "home_address", "postal_address"],
    # date of birth
    "birth": [
        "date_of_birth (MM-DD-YYYY)",
        "date_of_birth (DD-MM-YYYY)",
        "date_of_birth (MM/DD/YYYY)",
        "date_of_birth (DD/MM/YYYY)",
        "date_of_birth (YYYY/MM/DD)",
        "date_of_birth (YYYY-MM-DD)",
        "birth_date",
    ],
    "dob": [
        "date_of_birth (MM-DD-YYYY)",
        "date_of_birth (DD-MM-YYYY)",
        "date_of_birth (MM/DD/YYYY)",
        "date_of_birth (DD/MM/YYYY)",
        "date_of_birth (YYYY/MM/DD)",
        "date_of_birth (YYYY-MM-DD)",
        "birth_date",
    ],
    # generic date
    "date": ["current_date", "date"],
}


def detect_fill_entries(
    lines: List[str], keys: List[str], placeholder_pattern: re.Pattern,
    provider: Literal["openai", "groq", "anythingllm"]
) -> List[FillEntry]:
    """Detect fill entries in the document lines."""
    entries: List[FillEntry] = []
    # Find indices with placeholders
    indices = [i for i, l in enumerate(lines) if placeholder_pattern.search(l)]
    # Group contiguous lines within window of 3
    groups = []
    if indices:
        indices.sort()
        for i in indices:
            start = max(i - 1, 0)
            end = min(i + 1, len(lines) - 1)
            match = placeholder_pattern.search(lines[i])
            match_starts_at_0 = match is not None and match.start() == 0
            if (not groups or groups[-1][-1] < start) and not match_starts_at_0:
                new_group = list(range(start, end + 1))
                groups.append(new_group)
            elif groups and groups[-1][-1] < end:
                new_group = list(range(groups[-1][-1] + 1, end + 1))
                groups[-1].extend(new_group)
    # For each group, ask LLM to assign context keys
    for group in groups:
        entry_lines = "\n".join(lines[i] for i in group)
        num_spots = len(placeholder_pattern.findall(entry_lines))
        prompt = fill_entry_match_prompt(keys, entry_lines, num_spots)
        # Try parsing with retry logic for better reliability
        # If the LLM returns malformed JSON, we retry with increasingly specific instructions
        max_tries = 3
        parsed = None

        for try_count in range(max_tries):
            if try_count == 0:
                # First attempt with original prompt
                response = query_gpt(prompt, provider=provider)
            else:
                # Retry with more specific formatting instructions
                retry_prompt = fill_entry_retry_prompt(keys, entry_lines, num_spots)
                response = query_gpt(retry_prompt, provider=provider)

            # Clean and parse response
            clean = response.strip()
            clean = re.sub(r"^```(?:json)?\s*", "", clean)
            clean = re.sub(r"\s*```$", "", clean)

            # Look for JSON array pattern - be more careful with nested brackets
            # Find the outermost array brackets
            start_idx = clean.find("[")
            if start_idx != -1:
                bracket_count = 0
                end_idx = start_idx
                for i, char in enumerate(clean[start_idx:], start_idx):
                    if char == "[":
                        bracket_count += 1
                    elif char == "]":
                        bracket_count -= 1
                        if bracket_count == 0:
                            end_idx = i
                            break

                if bracket_count == 0:  # Found matching closing bracket
                    clean = clean[start_idx : end_idx + 1]
                else:
                    # Fallback to simple extraction
                    json_match = re.search(r"\[.*?\]", clean, re.DOTALL)
                    if json_match:
                        clean = json_match.group(0)

            try:
                parsed = json.loads(clean)
                logging.debug(
                    f"Successfully parsed JSON on attempt {try_count + 1}: {parsed}"
                )

                # Validate that we got the expected number of elements
                if len(parsed) != num_spots:
                    logging.warning(
                        f"Expected {num_spots} elements but got {len(parsed)}. Padding/truncating.\nText: {entry_lines}"
                    )
                    if len(parsed) < num_spots:
                        parsed.extend([None] * (num_spots - len(parsed)))
                    else:
                        parsed = parsed[:num_spots]

                # Validate that all non-null keys are part of the provided `keys` list
                invalid_keys = [
                    k for k in parsed if k not in (None, "null") and k not in keys
                ]
                if invalid_keys:
                    logging.warning(
                        f"Received keys that are not in AVAILABLE CONTEXT KEYS: {invalid_keys}. Retrying with clearer instructions."
                    )
                    # If we still have retries left, ask again with the clearer prompt
                    if try_count < max_tries - 1:
                        # Continue to next iteration which will build a stricter prompt
                        continue
                    else:
                        # Last attempt – replace invalid keys with None so downstream logic can handle them
                        parsed = [None if k in invalid_keys else k for k in parsed]

                # Successful parse – exit retry loop
                break

            except Exception as e:
                # Try to fix single quotes to double quotes
                try:
                    # Replace single quotes with double quotes, but be careful about apostrophes
                    fixed_clean = re.sub(r"'([^']*)'", r'"\1"', clean)
                    # Handle 'null' specifically
                    fixed_clean = re.sub(r"'null'", "null", fixed_clean)
                    parsed = json.loads(fixed_clean)
                    logging.debug(
                        f"Successfully parsed JSON after quote fixing on attempt {try_count + 1}: {parsed}"
                    )

                    # Validate that we got the expected number of elements
                    if len(parsed) != num_spots:
                        logging.warning(
                            f"Expected {num_spots} elements but got {len(parsed)}. Padding/truncating."
                        )
                        if len(parsed) < num_spots:
                            parsed.extend([None] * (num_spots - len(parsed)))
                        else:
                            parsed = parsed[:num_spots]

                    # Validate that all non-null keys are part of the provided `keys` list
                    invalid_keys = [
                        k for k in parsed if k not in (None, "null") and k not in keys
                    ]
                    if invalid_keys:
                        logging.warning(
                            f"Received keys that are not in AVAILABLE CONTEXT KEYS: {invalid_keys}. Retrying with clearer instructions."
                        )
                        # If we still have retries left, ask again with the clearer prompt
                        if try_count < max_tries - 1:
                            # Continue to next iteration which will build a stricter prompt
                            continue
                        else:
                            # Last attempt – replace invalid keys with None so downstream logic can handle them
                            parsed = [None if k in invalid_keys else k for k in parsed]

                    # Successful parse – exit retry loop
                    break
                except:
                    pass

                logging.warning(
                    f"Attempt {try_count + 1} failed to parse JSON. Response: '{response}', Cleaned: '{clean}', Error: {e}"
                )
                if try_count == max_tries - 1:
                    # Final attempt failed
                    logging.error(
                        f"All {max_tries} attempts failed to parse context_keys JSON from LLM. Using fallback."
                    )
                    parsed = cast(List[Optional[str]], [None] * num_spots)

        # After the retry loop ends, make sure we have a *parsed* list
        if parsed is None:
            parsed = cast(List[Optional[str]], [None] * num_spots)

        entries.append(FillEntry(lines=entry_lines, number_of_fill_spots=num_spots, context_keys=parsed))
    return entries


def process_fill_entries(
    entries: List[FillEntry], context_dir: str, placeholder_pattern: re.Pattern,
    provider: Literal["openai", "groq", "anythingllm"]
) -> List[FillEntry]:
    """Process fill entries by inferring missing context keys and filling values."""
    # Load or extract context data
    context_path = os.path.join(context_dir, "context_data.json")
    if os.path.exists(context_path):
        with open(context_path, "r", encoding="utf-8") as f:
            context_data = json.load(f)
    else:
        context_data = extract_context(context_dir, provider)
    missing_keys = []
    aggregated_corpus: Optional[str] = None
    for entry in entries:
        logging.debug("\n--- Processing FillEntry ---")
        logging.debug("Original entry lines:\n%s", entry.lines)
        logging.debug("Initial context key guesses: %s", entry.context_keys)
        # Keep a working copy of the entry text that we progressively fill
        partial_filled = entry.lines

        # Iterate through placeholders sequentially (global order)
        total_placeholders = len(entry.context_keys)
        search_pos = 0  # position to start the next search in partial_filled

        for idx in range(total_placeholders):
            # Locate next placeholder occurrence from current position
            match = placeholder_pattern.search(partial_filled, search_pos)
            if not match:
                break  # safety – should not happen

            # Determine line context and index on that line
            before_match = partial_filled[:match.start()]
            line_start = before_match.rfind('\n') + 1  # -1 becomes 0 so +1
            line_end = partial_filled.find('\n', match.start())
            if line_end == -1:
                line_end = len(partial_filled)
            line_text = partial_filled[line_start:line_end]

            # Count placeholders before this one on the same line
            prefix_line = line_text[: match.start() - line_start]
            idx_on_line = len(list(placeholder_pattern.findall(prefix_line)))

            key = entry.context_keys[idx]

            # Helper to replace this specific placeholder with a value
            def _replace_current_placeholder(text: str, replacement: str) -> str:
                """Replace current match span in *text* with *replacement* and return new text."""
                return text[: match.start()] + replacement + text[match.end():]

            value: str = ""
            if key and key != 'null':
                value = context_data.get(key, '')

            if value:  # We have a value, replace directly
                logging.debug("Replacing placeholder %s with key '%s' value '%s'", idx, key, value)
                partial_filled = _replace_current_placeholder(partial_filled, value)
                search_pos = match.start() + len(value)  # continue after inserted value
                continue  # move to next placeholder

            # Key missing or has no value – need to infer
            placeholder_context = line_text

            prompt = missing_key_inference_prompt(
                partial_filled,
                placeholder_context,
                idx_on_line,
                placeholder_pattern.pattern,
            )

            new_key = query_gpt(prompt, provider=provider).strip().strip('"')

            # Retrieve or mine value for new_key
            value = context_data.get(new_key, '')
            if not value:
                if aggregated_corpus is None:
                    try:
                        from .context_extractor import scan_context_dir, aggregate_text
                        files_in_ctx = scan_context_dir(context_dir)
                        aggregated_corpus = aggregate_text(files_in_ctx)
                    except Exception as e:
                        logging.error(f"Failed to build aggregated corpus from context folder '{context_dir}': {e}")
                        aggregated_corpus = ""

                if aggregated_corpus:
                    search_prompt = context_value_search_prompt(new_key, aggregated_corpus)
                    try:
                        raw_resp = query_gpt(search_prompt, provider=provider).strip()
                        cleaned_resp = raw_resp.strip('`').strip('"').strip("'")
                        if cleaned_resp.lower() != 'null' and cleaned_resp != "":
                            value = cleaned_resp
                            context_data[new_key] = value  # persist discovery
                            logging.info(f"Mined new context value for '{new_key}' from corpus.")
                    except Exception as e:
                        logging.error(f"LLM extraction for key '{new_key}' failed: {e}")

            # Record key mapping
            if new_key and entry.context_keys[idx] is None:
                entry.context_keys[idx] = new_key
            if not value:
                missing_keys.append(new_key)
                logging.info("Missing value for inferred key '%s' (placeholder %s)", new_key, idx)

            # Replace if we have a value
            if value:
                partial_filled = _replace_current_placeholder(partial_filled, value)
                search_pos = match.start() + len(value)
            else:
                # Skip this placeholder – move past it
                search_pos = match.end()

        # Save updated context_data after each entry
        with open(context_path, 'w', encoding='utf-8') as f:
            json.dump(context_data, f, ensure_ascii=False, indent=4)

        # Store the final filled text for this entry
        entry.filled_lines = partial_filled

        logging.debug("Filled entry lines:\n%s", entry.filled_lines)

    if missing_keys:
        logging.info("Total missing keys after processing: %s", list(set(missing_keys)))
    return entries
