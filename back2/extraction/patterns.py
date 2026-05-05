"""Detect placeholder patterns (regex) in form text."""

import re

# Candidate regex patterns we try, in priority order if tied.
_CANDIDATE_PATTERNS = [
    r"_{3,}",        # 3+ underscores
    r"\.{3,}",       # 3+ dots
    r"\[[\s_]{3,}\]",  # brackets containing spaces/underscores
    r"\(\s*\)",      # empty parentheses
    r"#{3,}",        # 3+ hashes
    r"-{3,}",        # 3+ dashes
]


def detect_placeholder_pattern(text: str) -> str:
    """
    Pick the candidate regex that yields the most matches in `text`.
    Falls back to underscores if nothing matches.
    """
    best_pattern = _CANDIDATE_PATTERNS[0]
    max_matches = 0
    for pattern in _CANDIDATE_PATTERNS:
        try:
            matches = re.findall(pattern, text)
        except re.error:
            continue
        if len(matches) > max_matches:
            max_matches = len(matches)
            best_pattern = pattern
    return best_pattern
