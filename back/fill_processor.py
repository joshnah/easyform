"""
Fill entry processing for form filling.

This module handles detection and processing of fill entries (placeholder fields)
in forms, including context key inference and value filling.
"""

import os
import re
import json
import logging
from dataclasses import dataclass
from typing import List, Optional, cast
from .context_extractor import extract_context
from .llm_client import query_gpt
from .prompts import fill_entry_match_prompt, fill_entry_retry_prompt


@dataclass
class FillEntry:
    lines: str
    number_of_fill_spots: int
    context_keys: List[Optional[str]]
    filled_lines: str = ''


# Heuristic keyword mapping to context keys. This is used as a fallback when the LLM
# cannot confidently map a placeholder to an existing key. The mapping should stay
# relatively small and generic so that it does not introduce incorrect matches.
# Extend this list over time as additional common placeholders are discovered.
COMMON_KEYWORD_MAPPING: dict[str, list[str]] = {
    # personal identity
    'name': [
        'full_name',
        'first_name',
        'last_name',
        'name'
    ],
    'first name': ['first_name'],
    'last name': ['last_name'],
    # contact
    'phone': ['phone_number', 'phone'],
    'telephone': ['phone_number', 'phone'],
    'mobile': ['phone_number', 'phone'],
    'email': ['email', 'email_address'],
    'e-mail': ['email', 'email_address'],
    'address': ['address', 'home_address', 'postal_address'],
    # date of birth
    'birth': [
        'date_of_birth (MM-DD-YYYY)',
        'date_of_birth (DD-MM-YYYY)',
        'date_of_birth (MM/DD/YYYY)',
        'date_of_birth (DD/MM/YYYY)',
        'date_of_birth (YYYY/MM/DD)',
        'date_of_birth (YYYY-MM-DD)',
        'birth_date',
    ],
    'dob': [
        'date_of_birth (MM-DD-YYYY)',
        'date_of_birth (DD-MM-YYYY)',
        'date_of_birth (MM/DD/YYYY)',
        'date_of_birth (DD/MM/YYYY)',
        'date_of_birth (YYYY/MM/DD)',
        'date_of_birth (YYYY-MM-DD)',
        'birth_date',
    ],
    # generic date
    'date': ['current_date', 'date'],
}


def detect_fill_entries(lines: List[str], keys: List[str], placeholder_pattern: re.Pattern) -> List[FillEntry]:
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
        entry_lines = '\n'.join(lines[i] for i in group)
        num_spots = len(placeholder_pattern.findall(entry_lines))
        prompt = fill_entry_match_prompt(keys, entry_lines, num_spots)
        # Try parsing with retry logic for better reliability
        # If the LLM returns malformed JSON, we retry with increasingly specific instructions
        max_tries = 3
        parsed = None
        
        for try_count in range(max_tries):
            if try_count == 0:
                # First attempt with original prompt
                response = query_gpt(prompt)
            else:
                # Retry with more specific formatting instructions
                retry_prompt = fill_entry_retry_prompt(keys, entry_lines, num_spots)
                response = query_gpt(retry_prompt)
            
            # Clean and parse response
            clean = response.strip()
            clean = re.sub(r"^```(?:json)?\s*", "", clean)
            clean = re.sub(r"\s*```$", "", clean)
            
            # Look for JSON array pattern - be more careful with nested brackets
            # Find the outermost array brackets
            start_idx = clean.find('[')
            if start_idx != -1:
                bracket_count = 0
                end_idx = start_idx
                for i, char in enumerate(clean[start_idx:], start_idx):
                    if char == '[':
                        bracket_count += 1
                    elif char == ']':
                        bracket_count -= 1
                        if bracket_count == 0:
                            end_idx = i
                            break
                
                if bracket_count == 0:  # Found matching closing bracket
                    clean = clean[start_idx:end_idx + 1]
                else:
                    # Fallback to simple extraction
                    json_match = re.search(r'\[.*?\]', clean, re.DOTALL)
                    if json_match:
                        clean = json_match.group(0)
            
            try:
                parsed = json.loads(clean)
                logging.debug(f"Successfully parsed JSON on attempt {try_count + 1}: {parsed}")
                
                # Validate that we got the expected number of elements
                if len(parsed) != num_spots:
                    logging.warning(f"Expected {num_spots} elements but got {len(parsed)}. Padding/truncating.\nText: {entry_lines}")
                    if len(parsed) < num_spots:
                        parsed.extend([None] * (num_spots - len(parsed)))
                    else:
                        parsed = parsed[:num_spots]
                
                # Validate that all non-null keys are part of the provided `keys` list
                invalid_keys = [k for k in parsed if k not in (None, 'null') and k not in keys]
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
                    logging.debug(f"Successfully parsed JSON after quote fixing on attempt {try_count + 1}: {parsed}")
                    
                    # Validate that we got the expected number of elements
                    if len(parsed) != num_spots:
                        logging.warning(f"Expected {num_spots} elements but got {len(parsed)}. Padding/truncating.")
                        if len(parsed) < num_spots:
                            parsed.extend([None] * (num_spots - len(parsed)))
                        else:
                            parsed = parsed[:num_spots]
                    
                    # Validate that all non-null keys are part of the provided `keys` list
                    invalid_keys = [k for k in parsed if k not in (None, 'null') and k not in keys]
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
                
                logging.warning(f"Attempt {try_count + 1} failed to parse JSON. Response: '{response}', Cleaned: '{clean}', Error: {e}")
                if try_count == max_tries - 1:
                    # Final attempt failed
                    logging.error(f"All {max_tries} attempts failed to parse context_keys JSON from LLM. Using fallback.")
                    parsed = cast(List[Optional[str]], [None] * num_spots)

        # After the retry loop ends, make sure we have a *parsed* list and run
        # heuristic mapping exactly once per group.
        if parsed is None:
            parsed = cast(List[Optional[str]], [None] * num_spots)

        _apply_keyword_heuristics(parsed, entry_lines, keys, placeholder_pattern)

        entries.append(FillEntry(lines=entry_lines, number_of_fill_spots=num_spots, context_keys=parsed))
    return entries


def process_fill_entries(entries: List[FillEntry], context_dir: str, placeholder_pattern: re.Pattern) -> List[FillEntry]:
    """Process fill entries by inferring missing context keys and filling values."""
    # Load or extract context data
    context_path = os.path.join(context_dir, 'context_data.json')
    if os.path.exists(context_path):
        with open(context_path, 'r', encoding='utf-8') as f:
            context_data = json.load(f)
    else:
        context_data = extract_context(context_dir)
    missing_keys = []
    # Lazy aggregated corpus for the context directory. We only build it if we
    # actually need to mine new values, and we build it only once.
    aggregated_corpus: Optional[str] = None
    for entry in entries:
        # Infer missing context_keys
        for i, key in enumerate(entry.context_keys):
            if key is None:
                # Find the specific placeholder text for better context
                placeholders = placeholder_pattern.findall(entry.lines)
                placeholder_context = ""
                if i < len(placeholders):
                    # Get surrounding text for this placeholder
                    lines_list = entry.lines.split('\n')
                    for line in lines_list:
                        if placeholder_pattern.search(line):
                            placeholder_context = line
                            break
                
                prompt = (
                    f"You are a form-filling assistant. Analyze this form text and suggest an appropriate context key name.\n\n"
                    f"FORM TEXT:\n{entry.lines}\n\n"
                    f"SPECIFIC PLACEHOLDER #{i+1}:\n{placeholder_context}\n\n"
                    f"INSTRUCTIONS:\n"
                    f"1. Look at the context around placeholder #{i+1} (the {i+1}{'st' if i==0 else 'nd' if i==1 else 'rd' if i==2 else 'th'} match of the placeholder pattern {placeholder_pattern.pattern})\n"
                    f"2. Determine what type of information should go in this placeholder\n"
                    f"3. Suggest a descriptive key name using snake_case (e.g., 'full_name', 'phone_number', 'birth_date')\n"
                    f"4. The person filling the form is always the USER themselves – avoid qualifiers like 'recipient', 'patient', 'applicant', etc.\n"
                    f"5. Pick the most general and concise key name possible (e.g., prefer 'name' over 'recipients_name').\n\n"
                    f"EXAMPLES:\n"
                    f"- 'Name: _______' → 'full_name'\n"
                    f"- 'Phone: _______' → 'phone_number'\n"
                    f"- 'Date of Birth: _______' → 'birth_date'\n"
                    f"- 'Recipient's Name: _______' → 'name'\n\n"
                    f"Respond with ONLY the key name (no quotes, no explanation):"
                )
                new_key = query_gpt(prompt).strip().strip('"')
                # Get value from context_data
                value = context_data.get(new_key, '')

                # If the value is not already in context_data, attempt to mine it
                # from the contents of the context folder using the LLM. We
                # replicate the spirit of context_extractor by first building an
                # aggregated textual corpus from every supported file in the
                # context folder and then asking the LLM for the specific key.
                if not value:
                    # Build corpus lazily (only once)
                    if aggregated_corpus is None:
                        try:
                            from .context_extractor import scan_context_dir, aggregate_text
                            files_in_ctx = scan_context_dir(context_dir)
                            aggregated_corpus = aggregate_text(files_in_ctx)
                        except Exception as e:
                            logging.error(f"Failed to build aggregated corpus from context folder '{context_dir}': {e}")
                            aggregated_corpus = ""

                    if aggregated_corpus:
                        search_prompt = (
                            f"You are an assistant tasked with retrieving information from a user's personal document corpus.\n\n"
                            f"REQUESTED KEY: {new_key}\n\n"
                            f"CORPUS:\n{aggregated_corpus}\n\n"
                            f"INSTRUCTIONS:\n"
                            f"1. Examine the corpus and determine the single most appropriate value for the requested key.\n"
                            f"2. If the information is clearly present, respond with ONLY that value.\n"
                            f"3. If the information is not present or you are uncertain, respond with the single word null (without quotes).\n"
                            f"4. Do NOT provide any additional text, explanation, or formatting."
                        )
                        try:
                            raw_resp = query_gpt(search_prompt).strip()
                            # Clean common wrapper artefacts (markdown, quotes)
                            cleaned_resp = raw_resp.strip('`').strip('\"').strip("'")
                            if cleaned_resp.lower() != 'null' and cleaned_resp != "":
                                value = cleaned_resp
                                # Persist new discovery
                                context_data[new_key] = value
                                logging.info(f"Mined new context value for '{new_key}' from corpus.")
                            else:
                                logging.info(f"No value found in corpus for key '{new_key}'.")
                        except Exception as e:
                            logging.error(f"LLM extraction for key '{new_key}' failed: {e}")

                if value:
                    entry.context_keys[i] = new_key
                else:
                    missing_keys.append(new_key)
        # Update context JSON file
        with open(context_path, 'w', encoding='utf-8') as f:
            json.dump(context_data, f, ensure_ascii=False, indent=4)
        # Fill lines using context values
        values = [context_data[k] if k and k != 'null' and k in context_data and context_data[k] != "" else None for k in entry.context_keys]

        # Use LLM to fill form line by line
        lines_list = entry.lines.split('\n')
        filled_lines = []
        
        for j in range(len(lines_list)):
            line = lines_list[j]
            
            # Check if this line has placeholders
            if placeholder_pattern.search(line):
                # Prepare prompt for LLM to fill this specific line
                prompt = (
                    f"You are a form-filling assistant. Fill the placeholders in the given line with appropriate values.\n\n"
                    f"FULL FORM CONTEXT:\n{entry.lines}\n\n"
                    f"AVAILABLE VALUES: {values}\n\n"
                    f"PLACEHOLDER PATTERN: {placeholder_pattern.pattern}\n\n"
                    f"INSTRUCTIONS:\n"
                    f"1. The i-th placeholder in the FULL FORM should be filled with values[i] if values[i] is not None\n"
                    f"2. If values[i] is None, leave the i-th placeholder unchanged\n"
                    f"3. Placeholders are matched by the pattern: {placeholder_pattern.pattern}\n"
                    f"4. Only modify the line I'm asking about, preserve all other formatting\n\n"
                    f"5. If the placeholder can be filled with a value, that placeholder MUST be FULLY replaced by the value\n"
                    f"LINE TO FILL (line {j+1}):\n{line}\n\n"
                    f"Respond with ONLY the filled version of this line, DO NOT include any other text:"
                )
                
                filled_line = query_gpt(prompt).strip()
                filled_lines.append(filled_line)
            else:
                # No placeholders in this line, keep as is
                filled_lines.append(line)
        
        entry.filled_lines = "\n".join(filled_lines)
    # # Pretty print the filled entries for inspection
    # import pprint
    # pprint.pprint([{
    #     "lines": entry.lines,
    #     "context_keys": entry.context_keys,
    #     "filled_lines": entry.filled_lines
    # } for entry in entries])
    return entries


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _apply_keyword_heuristics(parsed: List[Optional[str]],
                              entry_lines: str,
                              keys: List[str],
                              placeholder_pattern: re.Pattern) -> None:
    """Mutates *parsed* in-place by applying keyword heuristics to map
    placeholders that are still None to context keys.

    Args:
        parsed: The list of keys (or None) for each placeholder.
        entry_lines: The multiline string corresponding to the fill-entry
            block in the form.
        keys: The list of available context keys.
        placeholder_pattern: Regex used to identify placeholders. Needed so
            we can count placeholders within a line.
    """

    try:
        entry_line_list = entry_lines.lower().split('\n')

        for idx, key_name in enumerate(parsed):
            if key_name is None or key_name == 'null':
                # Locate the line that contains the idx-th placeholder.
                placeholder_counter = 0
                target_line = ''
                for l in entry_line_list:
                    matches = placeholder_pattern.findall(l)
                    if not matches:
                        continue
                    if placeholder_counter + len(matches) > idx:
                        target_line = l
                        break
                    placeholder_counter += len(matches)

                chosen_key: Optional[str] = None
                if target_line:
                    for keyword, candidate_keys in COMMON_KEYWORD_MAPPING.items():
                        if keyword in target_line:
                            for cand in candidate_keys:
                                if cand in keys:
                                    chosen_key = cand
                                    break
                            if chosen_key:
                                break

                if chosen_key:
                    parsed[idx] = chosen_key
                    logging.debug(
                        "Heuristic mapping: placeholder #%d in line '%s' -> %s",
                        idx + 1,
                        target_line.strip(),
                        chosen_key,
                    )
    except Exception as e:
        logging.error(f"Heuristic keyword mapping failed: {e}")