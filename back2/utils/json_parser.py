"""Robust JSON extraction from messy LLM responses."""

import json
import re
from typing import Any, Optional

_FENCE_OPEN = re.compile(r"^```(?:json)?\s*", re.IGNORECASE)
_FENCE_CLOSE = re.compile(r"\s*```$")
_ARRAY_RE = re.compile(r"(\[.*\])", re.DOTALL)
_OBJECT_RE = re.compile(r"(\{.*\})", re.DOTALL)


def parse_json_response(raw: str) -> Optional[Any]:
    """
    Best-effort parse of an LLM response that should be JSON.

    Strategy: strip code fences → try direct json.loads → fall back to first
    array or object substring. Returns None if every attempt fails.
    """
    if not raw:
        return None

    cleaned = _FENCE_OPEN.sub("", raw.strip())
    cleaned = _FENCE_CLOSE.sub("", cleaned)

    try:
        return json.loads(cleaned)
    except Exception:
        pass

    for pattern in (_ARRAY_RE, _OBJECT_RE):
        m = pattern.search(cleaned)
        if not m:
            continue
        try:
            return json.loads(m.group(1))
        except Exception:
            continue

    return None
