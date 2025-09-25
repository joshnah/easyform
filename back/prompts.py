# Prompt templates for filler_agent

EXTRACTION_PROMPT_TEMPLATE = '''
Assume the text describes the same person who will later fill the form (the USER). Extract the following personal information from the text below and return as a JSON object with keys:
- full_name
- first_name
- middle_names
- last_name
- birth_day
- birth_month
- birth_year
- date_of_birth (MM-DD-YYYY)
- date_of_birth (DD-MM-YYYY)
- date_of_birth (MM/DD/YYYY)
- date_of_birth (DD/MM/YYYY)
- date_of_birth (YYYY/MM/DD)
- date_of_birth (YYYY-MM-DD)
- phone_number
- email
- address

Text:
"""
{content}
"""

Return ONLY a valid JSON object with these keys. Use empty strings for missing fields, ONLY add the fields that are present in the text if you are sure about the value, otherwise leave it empty. Do not include any markdown formatting, code blocks, or explanatory text - just the raw JSON object.''' 

# ---------------------------------------------------------------------------
# Centralized prompt generation helpers
# ---------------------------------------------------------------------------

from typing import List, Optional


def placeholder_detection_prompt(form_text: str) -> str:
    return (
        "You are a form analysis assistant. Look at this form text and identify ALL placeholder strings that represent blank fields to be filled in.\n\n"
        f"FORM TEXT:\n{form_text}\n\n"
        "Find every placeholder string in the form that represents a field where information should be entered. "
        "These could be underscores, dots, dashes, text in brackets, text in parentheses, or any other pattern that indicates a fillable field.\n\n"
        "Respond with ONLY a JSON array containing the exact placeholder strings you find. "
        "Include each unique placeholder string exactly as it appears in the form. "
        "Format your response as a single line JSON array with no line breaks.\n\n"
        "Examples of what to look for:\n"
        "- _____ (underscores)\n"
        "- ..... (dots)\n"
        "- Any other pattern that clearly represents a fillable field\n\n"
        "Example response: [\"_____\", \"........\"]\n"
        "Your response:"
    )


def fill_entry_match_prompt(keys: List[str], entry_lines: str, num_spots: int) -> str:
    return (
        "You are a form-filling assistant. Your task is to match placeholders in form text to available context keys.\n\n"
        f"AVAILABLE CONTEXT KEYS: {keys}\n\n"
        f"FORM TEXT TO ANALYZE:\n{entry_lines}\n\n"
        "INSTRUCTIONS:\n"
        "1. Placeholders are sequences of underscores (e.g., _____, ________)\n"
        "2. The form refers to the USER filling it – avoid interpreting roles like 'recipient', 'applicant', etc.\n"
        "3. Examine each placeholder in the order they appear in the text\n"
        "4. For each placeholder, determine if any of the available context keys would provide the appropriate information to fill it (prefer the most general key when multiple match)\n"
        "5. Only match a key if you are confident it's the correct information for that placeholder. The key must be in the list of AVAILABLE CONTEXT KEYS\n"
        "6. If no key matches or you're unsure, use null\n\n"
        "EXAMPLE:\n"
        "Text: 'Name: _______ Date: _______'\n"
        "Keys: ['full_name', 'birth_date', 'address']\n"
        "Response: ['full_name', 'birth_date']\n\n"
        f"Respond with ONLY a JSON array of {num_spots} elements (keys or null):"
    )


def fill_entry_retry_prompt(keys: List[str], entry_lines: str, num_spots: int) -> str:
    base_prompt = fill_entry_match_prompt(keys, entry_lines, num_spots)
    return (
        "IMPORTANT: Your previous response could not be parsed as JSON. Please respond with EXACTLY the format requested.\n\n"
        f"{base_prompt}\n\n"
        "CRITICAL FORMATTING REQUIREMENTS:\n"
        "1. Respond with ONLY a JSON array, nothing else\n"
        "2. Use double quotes, not single quotes\n"
        "3. Use null (not None) for missing values\n"
        "4. Do not include any explanations or code blocks\n"
        f"5. The array must have exactly {num_spots} elements\n"
        "6. Each element must be either null or one of the AVAILABLE CONTEXT KEYS exactly as provided (case-sensitive)\n\n"
        'Example of correct format: [null, "key_name", null]\n'
        "Your response:"
    )


def checkbox_context_key_prompt(keys: List[str], group_text: str, checkbox_values: List[str]) -> str:
    return (
        f"You are a form-filling assistant. Analyze this checkbox group and determine which context key is most relevant.\n\n"
        f"AVAILABLE CONTEXT KEYS: {keys}\n\n"
        f"CHECKBOX GROUP:\n{group_text}\n\n"
        f"CHECKBOX OPTIONS: {checkbox_values}\n\n"
        "INSTRUCTIONS:\n"
        "1. Look at the context around the checkboxes\n"
        "2. Remember the form is about the USER themselves; avoid role-specific prefixes (e.g., 'applicant', 'patient').\n"
        "3. Determine what type of information these checkboxes represent\n"
        "4. Find the most relevant context key from the available keys (use the most general name possible)\n"
        "5. If no key is clearly relevant, respond with 'none'\n\n"
        "EXAMPLES:\n"
        "- Checkboxes for 'Gender: [ ] Male [ ] Female' → 'gender'\n"
        "- Checkboxes for 'Marital Status: [ ] Single [ ] Married' → 'marital_status'\n"
        "- Checkboxes for 'Education: [ ] High School [ ] College' → 'education'\n\n"
        "Respond with ONLY the key name or 'none' (no quotes, no explanation):"
    )


def checkbox_infer_key_prompt(group_text: str, checkbox_values: List[str]) -> str:
    return (
        f"You are a form-filling assistant. Analyze this checkbox group and suggest an appropriate context key name.\n\n"
        f"CHECKBOX GROUP:\n{group_text}\n\n"
        f"CHECKBOX OPTIONS: {checkbox_values}\n\n"
        "INSTRUCTIONS:\n"
        "1. Look at the context around the checkboxes\n"
        "2. Determine what type of information these checkboxes represent\n"
        "3. Suggest a descriptive key name using snake_case (e.g., 'gender', 'marital_status', 'education_level')\n"
        "4. The form is filled by the USER – avoid qualifiers like 'applicant', 'patient', 'recipient', etc.\n"
        "5. Use the most general and concise key name possible (e.g., 'gender' not 'applicant_gender').\n\n"
        "EXAMPLES:\n"
        "- 'Gender: [ ] Male [ ] Female' → 'gender'\n"
        "- 'Marital Status: [ ] Single [ ] Married' → 'marital_status'\n"
        "- 'Education: [ ] High School [ ] College' → 'education_level'\n"
        "- 'Applicant Gender: [ ] Male [ ] Female' → 'gender'\n\n"
        "Respond with ONLY the key name (no quotes, no explanation):"
    )


def checkbox_selection_prompt(context_key: str, context_value: str, checkbox_values: List[str]) -> str:
    return (
        "You are a form-filling assistant. Determine which checkboxes should be checked based on the context value.\n\n"
        f"CONTEXT KEY: {context_key}\n"
        f"CONTEXT VALUE: {context_value}\n\n"
        f"CHECKBOX OPTIONS: {checkbox_values}\n\n"
        "INSTRUCTIONS:\n"
        "1. Compare the context value with each checkbox option\n"
        "2. Determine which checkbox options match or are most relevant to the context value\n"
        "3. Return the indices (0-based) of checkboxes that should be checked\n"
        "4. If no checkboxes should be checked, return an empty array\n"
        "5. Multiple checkboxes can be checked if appropriate\n\n"
        "EXAMPLES:\n"
        "Context: 'Male', Options: ['Male', 'Female'] → [0]\n"
        "Context: 'Single', Options: ['Single', 'Married', 'Divorced'] → [0]\n"
        "Context: 'Bachelor Degree', Options: ['High School', 'College', 'Graduate'] → [1]\n\n"
        "Respond with ONLY a JSON array of indices (e.g., [0], [1, 2], or []):"
    )

# ---------------------------------------------------------------------------
# Additional prompt helpers used by process_fill_entries in fill_processor.py
# ---------------------------------------------------------------------------

def _ordinal_suffix(index: int) -> str:
    """Return the ordinal suffix for 1-based *index* (e.g., 1 -> 'st')."""
    if 10 <= (index % 100) <= 20:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(index % 10, "th")


def missing_key_inference_prompt(
    entry_lines: str,
    placeholder_context: str,
    placeholder_idx_in_line_zero_based: int,
    placeholder_pattern: str,
) -> str:
    """Prompt for suggesting a context key name for a missing placeholder.

    Args:
        entry_lines: Full text of the form block being analysed.
        placeholder_context: The specific line (or snippet) containing the placeholder.
        placeholder_idx_in_line_zero_based: Index of the placeholder on its line (0-based).
        placeholder_pattern: Regex pattern string that identifies placeholders.

    Returns:
        A fully-formed prompt string.
    """
    j = placeholder_idx_in_line_zero_based + 1
    ordinal_line = _ordinal_suffix(j)
    return (
        "You are a form-filling assistant. Analyze this form text and suggest an appropriate context key name.\n\n"
        f"FORM TEXT:\n{entry_lines}\n\n"
        f"SPECIFIC PLACEHOLDER CONTEXT:\n{placeholder_context}\n\n"
        "INSTRUCTIONS:\n"
        f"1. Look at the context around the placeholder pattern {placeholder_pattern}.\n"
        f"2. On its line, this is the {j}{ordinal_line} placeholder (counting from left to right if multiple placeholders exist).\n"
        "3. Determine what type of information should go in this placeholder\n"
        "4. Suggest a descriptive key name using snake_case (e.g., 'full_name', 'phone_number', 'birth_date')\n"
        "5. The person filling the form is always the USER themselves – avoid qualifiers like 'recipient', 'patient', 'applicant', etc.\n"
        "6. Pick the most general and concise key name possible (e.g., prefer 'name' over 'recipients_name').\n\n"
        "EXAMPLES:\n"
        "- 'Name: _______' → 'full_name'\n"
        "- 'Phone: _______' → 'phone_number'\n"
        "- 'Date of Birth: _______' → 'birth_date'\n"
        "- 'Recipient's Name: _______' → 'name'\n\n"
        "Respond with ONLY the key name (no quotes, no explanation):"
    )


def context_value_search_prompt(new_key: str, aggregated_corpus: str) -> str:
    """Prompt for retrieving a value for *new_key* from *aggregated_corpus*."""
    return (
        "You are an assistant tasked with retrieving information from a user's personal document corpus.\n\n"
        f"REQUESTED KEY: {new_key}\n\n"
        f"CORPUS:\n{aggregated_corpus}\n\n"
        "INSTRUCTIONS:\n"
        "1. Examine the corpus and determine the single most appropriate value for the requested key.\n"
        "2. If the information is clearly present, respond with ONLY that value.\n"
        "3. If the information is not present or you are uncertain, respond with the single word null (without quotes).\n"
        "4. Do NOT provide any additional text, explanation, or formatting."
    )