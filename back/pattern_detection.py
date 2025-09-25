"""
Pattern detection utilities for form filling.

This module handles detection of placeholder patterns in forms using LLM-based
analysis and provides regex patterns for various form elements.
"""

import re
import json
import logging
from .llm_client import query_gpt
from .prompts import placeholder_detection_prompt
from typing import Literal

# Default fallback pattern - will be replaced by dynamic detection
DEFAULT_PLACEHOLDER_PATTERN = re.compile(r'_+')
CHECKBOX_PATTERN = re.compile(r'[\[\(][\sXx]?[\]\)]|[☐☑☒□■]')


def detect_placeholder_patterns(
        form_text: str,
        provider: Literal['openai', 'groq', 'anythingllm']
    ) -> re.Pattern:
    """
    Use LLM to detect actual placeholder strings in the form text and return a combined regex pattern.
    Falls back to default underscore pattern if detection fails.
    """
    prompt = placeholder_detection_prompt(form_text)
    
    # Try parsing with retry logic
    max_tries = 3
    placeholder_strings = None
    
    for try_count in range(max_tries):
        # response = query_gpt(prompt)
        response = query_gpt(prompt=prompt, provider=provider)
        
        # Clean and parse response
        clean = response.strip()
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
        
        # Look for JSON array pattern - handle multi-line arrays
        # Find the first '[' and the last ']' to capture the complete array
        start_idx = clean.find('[')
        end_idx = clean.rfind(']')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            clean = clean[start_idx:end_idx + 1]
        else:
            # Fallback: try the original regex approach
            json_match = re.search(r'\[.*?\]', clean, re.DOTALL)
            if json_match:
                clean = json_match.group(0)
        
        # Remove any line breaks within the JSON string that might break parsing
        # but preserve the structure
        try:
            # First attempt: try parsing as-is
            placeholder_strings = json.loads(clean)
            if isinstance(placeholder_strings, list) and all(isinstance(p, str) for p in placeholder_strings):
                logging.debug(f"Successfully parsed placeholder strings on attempt {try_count + 1}: {placeholder_strings}")
                break
            else:
                raise ValueError("Not a list of strings")
                
        except json.JSONDecodeError:
            # Second attempt: try to fix common JSON formatting issues
            try:
                # Remove line breaks within quoted strings and normalize whitespace
                fixed_clean = re.sub(r'"\s*\n\s*', '"', clean)
                fixed_clean = re.sub(r'\n\s*"', ', "', fixed_clean)
                fixed_clean = re.sub(r'\[\s*\n\s*', '[', fixed_clean)
                fixed_clean = re.sub(r'\s*\n\s*\]', ']', fixed_clean)
                
                placeholder_strings = json.loads(fixed_clean)
                if isinstance(placeholder_strings, list) and all(isinstance(p, str) for p in placeholder_strings):
                    logging.debug(f"Successfully parsed placeholder strings after fixing on attempt {try_count + 1}: {placeholder_strings}")
                    break
                else:
                    raise ValueError("Not a list of strings")
                    
            except Exception as e:
                logging.warning(f"Attempt {try_count + 1} failed to parse placeholder strings. Response: '{response}', Cleaned: '{clean}', Error: {e}")
                if try_count == max_tries - 1:
                    logging.error(f"All {max_tries} attempts failed to parse placeholder strings. Using default pattern.")
                    placeholder_strings = []
        except Exception as e:
            logging.warning(f"Attempt {try_count + 1} failed to parse placeholder strings. Response: '{response}', Cleaned: '{clean}', Error: {e}")
            if try_count == max_tries - 1:
                logging.error(f"All {max_tries} attempts failed to parse placeholder strings. Using default pattern.")
                placeholder_strings = []
    
    if not placeholder_strings:
        logging.warning("No placeholder strings found, using default underscore pattern")
        return DEFAULT_PLACEHOLDER_PATTERN
    
    # Create regex patterns from the actual placeholder strings
    valid_patterns = []
    for placeholder in placeholder_strings:
        if placeholder.strip():  # Skip empty strings
            # Escape special regex characters in the placeholder string
            escaped_placeholder = re.escape(placeholder)
            valid_patterns.append(escaped_placeholder)
            logging.debug(f"Added pattern for placeholder '{placeholder}': {escaped_placeholder}")
    
    if not valid_patterns:
        logging.warning("No valid placeholder patterns found, using default underscore pattern")
        return DEFAULT_PLACEHOLDER_PATTERN
    
    # Sort patterns by descending length so longer placeholders are matched before shorter ones
    valid_patterns.sort(key=len, reverse=True)

    # Combine patterns with OR operator
    combined_pattern = "|".join(f"({pattern})" for pattern in valid_patterns)
    
    try:
        compiled_pattern = re.compile(combined_pattern)
        logging.info(f"Created dynamic placeholder pattern from {len(valid_patterns)} placeholders: {combined_pattern}")
        return compiled_pattern
    except re.error as e:
        logging.error(f"Failed to compile combined pattern '{combined_pattern}': {e}")
        logging.info("Falling back to default underscore pattern")
        return DEFAULT_PLACEHOLDER_PATTERN 
