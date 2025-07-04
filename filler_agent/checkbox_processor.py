"""
Checkbox processing for form filling.

This module handles detection, processing, and updating of checkboxes in forms,
including matching checkbox groups to context keys and determining which should be checked.
"""

import os
import re
import json
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple
from .pattern_detection import CHECKBOX_PATTERN
from .context_extractor import extract_context
from .llm_client import query_gpt


@dataclass
class CheckboxEntry:
    lines: str
    checkbox_positions: List[Tuple[int, int]]  # (line_index, char_index) for each checkbox
    checkbox_values: List[str]  # The text options for each checkbox
    context_key: Optional[str] = None
    checked_indices: List[int] = None  # Which checkboxes should be checked


def detect_checkbox_entries(lines: List[str], keys: List[str]) -> List[CheckboxEntry]:
    """Detect checkbox entries in the document lines."""
    entries: List[CheckboxEntry] = []
    
    # Find lines with checkboxes
    checkbox_lines = []
    for i, line in enumerate(lines):
        if CHECKBOX_PATTERN.search(line):
            checkbox_lines.append(i)
    
    if not checkbox_lines:
        return entries
    
    # Group contiguous checkbox lines (within window of 3)
    groups = []
    current = [checkbox_lines[0]]
    for idx in checkbox_lines[1:]:
        if idx - current[-1] <= 1 and len(current) < 3:  # Allow up to 1 line gap, max 3 lines total
            current.append(idx)
        else:
            groups.append(current)
            current = [idx]
    groups.append(current)
    
    # Process each group
    for group in groups:
        # Get context lines (include 1 line before and after if available)
        start_idx = max(0, group[0] - 1)
        end_idx = min(len(lines), group[-1] + 2)
        context_lines = lines[start_idx:end_idx]
        context_text = '\n'.join(context_lines)
        
        # Find all checkboxes and their positions within the group
        checkbox_positions = []
        checkbox_values = []
        
        for line_idx in group:
            line = lines[line_idx]
            relative_line_idx = line_idx - start_idx  # Position within context_lines
            
            # Find checkboxes in this line
            for match in CHECKBOX_PATTERN.finditer(line):
                char_idx = match.start()
                checkbox_positions.append((relative_line_idx, char_idx))
                
                # Extract the text associated with this checkbox (text after the checkbox)
                remaining_text = line[match.end():].strip()
                # Take text until next checkbox or end of line
                next_checkbox = CHECKBOX_PATTERN.search(remaining_text)
                if next_checkbox:
                    checkbox_text = remaining_text[:next_checkbox.start()].strip()
                else:
                    checkbox_text = remaining_text
                
                checkbox_values.append(checkbox_text)
        
        if checkbox_positions:
            entries.append(CheckboxEntry(
                lines=context_text,
                checkbox_positions=checkbox_positions,
                checkbox_values=checkbox_values
            ))
    
    return entries


def process_checkbox_entries(entries: List[CheckboxEntry], context_dir: str, keys: List[str]) -> List[CheckboxEntry]:
    """Process checkbox entries by matching them to context keys and determining which should be checked."""
    # Load or extract context data
    context_path = os.path.join(context_dir, 'context_data.json')
    if os.path.exists(context_path):
        with open(context_path, 'r', encoding='utf-8') as f:
            context_data = json.load(f)
    else:
        context_data = extract_context(context_dir)
    
    for entry in entries:
        # Ask LLM to match this checkbox group to a context key
        prompt = (
            f"You are a form-filling assistant. Analyze this checkbox group and determine which context key is most relevant.\n\n"
            f"AVAILABLE CONTEXT KEYS: {keys}\n\n"
            f"CHECKBOX GROUP:\n{entry.lines}\n\n"
            f"CHECKBOX OPTIONS: {entry.checkbox_values}\n\n"
            f"INSTRUCTIONS:\n"
            f"1. Look at the context around the checkboxes\n"
            f"2. Remember the form is about the USER themselves; avoid role-specific prefixes (e.g., 'applicant', 'patient').\n"
            f"3. Determine what type of information these checkboxes represent\n"
            f"4. Find the most relevant context key from the available keys (use the most general name possible)\n"
            f"5. If no key is clearly relevant, respond with 'none'\n\n"
            f"EXAMPLES:\n"
            f"- Checkboxes for 'Gender: [ ] Male [ ] Female' → 'gender'\n"
            f"- Checkboxes for 'Marital Status: [ ] Single [ ] Married' → 'marital_status'\n"
            f"- Checkboxes for 'Education: [ ] High School [ ] College' → 'education'\n\n"
            f"Respond with ONLY the key name or 'none' (no quotes, no explanation):"
        )
        
        response = query_gpt(prompt).strip().strip('"').lower()
        
        if response == 'none' or response not in keys:
            # Try to infer a new context key
            infer_prompt = (
                f"You are a form-filling assistant. Analyze this checkbox group and suggest an appropriate context key name.\n\n"
                f"CHECKBOX GROUP:\n{entry.lines}\n\n"
                f"CHECKBOX OPTIONS: {entry.checkbox_values}\n\n"
                f"INSTRUCTIONS:\n"
                f"1. Look at the context around the checkboxes\n"
                f"2. Determine what type of information these checkboxes represent\n"
                f"3. Suggest a descriptive key name using snake_case (e.g., 'gender', 'marital_status', 'education_level')\n"
                f"4. The form is filled by the USER – avoid qualifiers like 'applicant', 'patient', 'recipient', etc.\n"
                f"5. Use the most general and concise key name possible (e.g., 'gender' not 'applicant_gender').\n\n"
                f"EXAMPLES:\n"
                f"- 'Gender: [ ] Male [ ] Female' → 'gender'\n"
                f"- 'Marital Status: [ ] Single [ ] Married' → 'marital_status'\n"
                f"- 'Education: [ ] High School [ ] College' → 'education_level'\n"
                f"- 'Applicant Gender: [ ] Male [ ] Female' → 'gender'\n\n"
                f"Respond with ONLY the key name (no quotes, no explanation):"
            )
            
            inferred_key = query_gpt(infer_prompt).strip().strip('"').lower()
            
            # Check if we have a value for this key in context_data
            context_value = context_data.get(inferred_key, '')
            if not context_value:
                # Try to extract this information from context files
                logging.info(f"Attempting to extract value for inferred key: {inferred_key}")
                # This will use the existing context extraction logic
                context_data = extract_context(context_dir)
                context_value = context_data.get(inferred_key, '')
            
            if context_value:
                entry.context_key = inferred_key
                # Update context JSON file
                with open(context_path, 'w', encoding='utf-8') as f:
                    json.dump(context_data, f, ensure_ascii=False, indent=4)
            else:
                logging.info(f"No value found for checkbox group, skipping: {entry.lines[:50]}...")
                continue
        else:
            entry.context_key = response
            context_value = context_data.get(response, '')
        
        # Now determine which checkboxes should be checked based on the context value
        if entry.context_key and context_value:
            selection_prompt = (
                f"You are a form-filling assistant. Determine which checkboxes should be checked based on the context value.\n\n"
                f"CONTEXT KEY: {entry.context_key}\n"
                f"CONTEXT VALUE: {context_value}\n\n"
                f"CHECKBOX OPTIONS: {entry.checkbox_values}\n\n"
                f"INSTRUCTIONS:\n"
                f"1. Compare the context value with each checkbox option\n"
                f"2. Determine which checkbox options match or are most relevant to the context value\n"
                f"3. Return the indices (0-based) of checkboxes that should be checked\n"
                f"4. If no checkboxes should be checked, return an empty array\n"
                f"5. Multiple checkboxes can be checked if appropriate\n\n"
                f"EXAMPLES:\n"
                f"Context: 'Male', Options: ['Male', 'Female'] → [0]\n"
                f"Context: 'Single', Options: ['Single', 'Married', 'Divorced'] → [0]\n"
                f"Context: 'Bachelor Degree', Options: ['High School', 'College', 'Graduate'] → [1]\n\n"
                f"Respond with ONLY a JSON array of indices (e.g., [0], [1, 2], or []):"
            )
            
            # Try parsing with retry logic
            max_tries = 3
            parsed_indices = None
            
            for try_count in range(max_tries):
                if try_count == 0:
                    response = query_gpt(selection_prompt)
                else:
                    retry_prompt = (
                        f"IMPORTANT: Your previous response could not be parsed as JSON. Please respond with EXACTLY the format requested.\n\n"
                        f"{selection_prompt}\n\n"
                        f"CRITICAL FORMATTING REQUIREMENTS:\n"
                        f"1. Respond with ONLY a JSON array of numbers, nothing else\n"
                        f"2. Use square brackets [ ]\n"
                        f"3. Use integers for indices (0, 1, 2, etc.)\n"
                        f"4. Separate multiple indices with commas\n"
                        f"5. Do not include any explanations or code blocks\n\n"
                        f"Example of correct format: [0] or [1, 2] or []\n"
                        f"Your response:"
                    )
                    response = query_gpt(retry_prompt)
                
                # Clean and parse response
                clean = response.strip()
                clean = re.sub(r"^```(?:json)?\s*", "", clean)
                clean = re.sub(r"\s*```$", "", clean)
                
                # Look for JSON array pattern
                json_match = re.search(r'\[.*?\]', clean)
                if json_match:
                    clean = json_match.group(0)
                
                try:
                    parsed_indices = json.loads(clean)
                    if isinstance(parsed_indices, list) and all(isinstance(i, int) for i in parsed_indices):
                        # Validate indices are within range
                        valid_indices = [i for i in parsed_indices if 0 <= i < len(entry.checkbox_values)]
                        entry.checked_indices = valid_indices
                        logging.debug(f"Successfully parsed checkbox indices: {valid_indices}")
                        break
                    else:
                        raise ValueError("Not a list of integers")
                        
                except Exception as e:
                    logging.warning(f"Attempt {try_count + 1} failed to parse checkbox indices. Response: '{response}', Cleaned: '{clean}', Error: {e}")
                    if try_count == max_tries - 1:
                        logging.error(f"All {max_tries} attempts failed to parse checkbox indices. Skipping checkbox group.")
                        entry.checked_indices = []
    
    return entries


def update_checkbox_in_paragraph(para, char_idx: int, should_check: bool):
    """Update a checkbox character in a paragraph at the specified character index."""
    # Mapping of checkbox characters
    checkbox_mappings = {
        # Unchecked -> Checked
        '[ ]': '[X]',
        '[]': '[X]',
        '( )': '(X)',
        '()': '(X)',
        '☐': '☑',
        '□': '■',
        # Already checked patterns (keep as is if should_check=True, uncheck if should_check=False)
        '[X]': '[X]' if should_check else '[ ]',
        '[x]': '[x]' if should_check else '[ ]',
        '(X)': '(X)' if should_check else '( )',
        '(x)': '(x)' if should_check else '( )',
        '☑': '☑' if should_check else '☐',
        '☒': '☒' if should_check else '☐',
        '■': '■' if should_check else '□',
    }
    
    # Find the run containing the character at char_idx
    current_pos = 0
    for run in para.runs:
        run_text = run.text
        if current_pos <= char_idx < current_pos + len(run_text):
            # This run contains our checkbox
            relative_idx = char_idx - current_pos
            
            # Find the checkbox pattern at this position
            for pattern, replacement in checkbox_mappings.items():
                pattern_len = len(pattern)
                if (relative_idx + pattern_len <= len(run_text) and 
                    run_text[relative_idx:relative_idx + pattern_len] == pattern):
                    
                    # Determine the replacement based on should_check
                    if should_check:
                        if pattern in ['[ ]', '[]']:
                            new_text = '[X]'
                        elif pattern in ['( )', '()']:
                            new_text = '(X)'
                        elif pattern == '☐':
                            new_text = '☑'
                        elif pattern == '□':
                            new_text = '■'
                        else:
                            new_text = pattern  # Already checked
                    else:
                        if pattern in ['[X]', '[x]']:
                            new_text = '[ ]'
                        elif pattern in ['(X)', '(x)']:
                            new_text = '( )'
                        elif pattern in ['☑', '☒']:
                            new_text = '☐'
                        elif pattern == '■':
                            new_text = '□'
                        else:
                            new_text = pattern  # Already unchecked
                    
                    # Replace the text in the run
                    run.text = (run_text[:relative_idx] + 
                               new_text + 
                               run_text[relative_idx + pattern_len:])
                    
                    logging.debug(f"Updated checkbox: '{pattern}' -> '{new_text}' (should_check={should_check})")
                    return
            
            # If no exact pattern match, try to find any checkbox pattern nearby
            for match in CHECKBOX_PATTERN.finditer(run_text[max(0, relative_idx-2):relative_idx+5]):
                match_start = max(0, relative_idx-2) + match.start()
                match_end = max(0, relative_idx-2) + match.end()
                pattern = run_text[match_start:match_end]
                
                # Apply the same logic as above
                if should_check:
                    if pattern in ['[ ]', '[]']:
                        new_text = '[X]'
                    elif pattern in ['( )', '()']:
                        new_text = '(X)'
                    elif pattern == '☐':
                        new_text = '☑'
                    elif pattern == '□':
                        new_text = '■'
                    else:
                        new_text = pattern  # Already checked or unknown
                else:
                    if pattern in ['[X]', '[x]']:
                        new_text = '[ ]'
                    elif pattern in ['(X)', '(x)']:
                        new_text = '( )'
                    elif pattern in ['☑', '☒']:
                        new_text = '☐'
                    elif pattern == '■':
                        new_text = '□'
                    else:
                        new_text = pattern  # Already unchecked or unknown
                
                run.text = (run_text[:match_start] + 
                           new_text + 
                           run_text[match_end:])
                
                logging.debug(f"Updated nearby checkbox: '{pattern}' -> '{new_text}' (should_check={should_check})")
                return
            
            break
        current_pos += len(run_text)
    
    logging.warning(f"Could not find checkbox at character index {char_idx} in paragraph") 