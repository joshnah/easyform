"""Prompts for the back2 document-first workflow."""

from typing import List, Tuple


def field_analysis_prompt(fields: List[Tuple[str, str]]) -> str:
    """
    Batch prompt: infer field_type and a snake_case context key for each field.

    `fields` is a list of (line_text, surrounding_context) tuples. The model
    must respond with a JSON array, one object per input field, in order.
    """
    blocks = []
    for i, (line, ctx) in enumerate(fields, start=1):
        blocks.append(f"Field {i}: {line}\n Context {i}: {ctx}\n")
    fields_text = "\n".join(blocks)

    return f"""
        Analyze the following form fields (in order). For each field, determine:
        1) the single best field_type
        2) a key (snake_case) to look up this value in context data; this must not be null.
        3) Return one result per (FIELD, CONTEXT) pair, in the same order.

        Do not invent values. If uncertain, use null for key.

        INPUT FIELDS:
        {fields_text}

        RESPONSE FORMAT (MUST BE EXACT):
        Return ONLY a JSON array with one object per input field (same order). Each object must have exactly:
        [
            {{"field_type": "<field_type>", "key": "<snake_case_or_null>"}},
        ...
        ]

        EXAMPLES:

        Example 1:
        INPUT:
        Field 1: Line: "Name: _______"
        Context 1: "Please print your full name."
        Field 2: Line: "Favorite Color: _______"
        Context 2: "What is your favorite color?"
        RESPONSE:
        [
            {{"field_type": "name", "key": "full_name"}},
            {{"field_type": "other", "key": "favorite_color"}}
        ]

        Example 2 (mixed):
        INPUT:
        Field 1: Line: "Email: _______"
        Context 1: "We'll contact you at this address."
        Field 2: Line: "Hobby: _______"
        Context 2: "List your primary hobby."
        RESPONSE:
        [
            {{"field_type": "email", "key": "email"}},
            {{"field_type": "other", "key": "hobby"}}
        ]

        Respond NOW with ONLY the JSON array (no commentary, no code fences).
    """


def context_search_prompt(
    context_key: List[str], field_type: List[str], all_text: str
) -> str:
    """
    Batch prompt: extract values for the requested context keys from `all_text`.

    `context_key` and `field_type` are aligned lists. The model must respond
    with a JSON array of {context_key, value} objects in input order.
    """
    blocks = []
    for i, (key, ftype) in enumerate(zip(context_key, field_type), start=1):
        blocks.append(f"ITEM {i}:\nContext Key: {key}\nField Type: {ftype}\n")
    inputs_text = "\n".join(blocks)

    return f"""
        Search the provided text for the exact values corresponding to the requested context keys.

        INPUT ITEMS (in order):
        {inputs_text}

        TEXT:
        {all_text}

        INSTRUCTIONS:
        1. For each ITEM, locate an explicit value in the text matching the Context Key and Field Type.
        2. Extract the exact value (do not normalize unless clearly standard, e.g., emails).
        3. If you cannot find an explicit value, use an empty string for that item.
        4. Do NOT invent or infer values that are not present.
        5. Respond with ONLY a JSON array. Each element must be:
           - "context_key": echo of the requested key
           - "value": extracted string value or empty string

        RESPONSE FORMAT (MUST BE EXACT):
        [
            {{"context_key": "<key1>", "value": "<extracted_value_or_empty_string>"}},
            {{"context_key": "<key2>", "value": "<extracted_value_or_empty_string>"}},
            ...
        ]

        EXAMPLES:

        Example 1:
        INPUT:
        Item 1: Context Key: "full_name" | Field Type: "name"
        Text: "Applicant: Amelia Mary Quest, born 1990"

        Item 2: Context Key: "email" | Field Type: "email"
        Text: "Contact: amelia.quest@example.com"

        RESPONSE:
        [
            {{"context_key": "full_name", "value": "Amelia Mary Quest"}},
            {{"context_key": "email", "value": "amelia.quest@example.com"}}
        ]

        Example 2 (missing info):
        INPUT:
        Item 1: Context Key: "phone" | Field Type: "phone"
        Text: "No phone listed"

        RESPONSE:
        [
            {{"context_key": "phone", "value": ""}}
        ]

        Respond NOW with ONLY the JSON array (maintain input order).
    """
