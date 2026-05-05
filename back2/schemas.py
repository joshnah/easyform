from typing import Optional
from dataclasses import dataclass


@dataclass
class FieldRequirement:
    """A field detected in a document that needs to be filled."""

    field_id: str
    field_text: str
    line_number: int
    placeholder_pattern: str
    surrounding_context: str
    field_type: Optional[str] = None
    context_key: Optional[str] = None
    match_position: Optional[int] = None
    value: Optional[str] = None
