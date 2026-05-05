"""Token counting for batch budgeting.

Uses the Rust-backed `tokenizers` library if `back2/tokenizer.json` is shipped
alongside the package. Falls back to a char-count heuristic (`len // 4`) if
the file or the library is missing — approximate but plenty for batch sizing,
since `CONTEXT_WINDOW` is already conservative.

This module is the only place that knows whether we have a real tokenizer.
Callers always go through `count_tokens(text)`.
"""

import logging
from typing import Callable, Optional

from back2.paths import resource_path

logger = logging.getLogger(__name__)

_COUNT_TOKENS: Optional[Callable[[str], int]] = None


def _char_estimate(text: str) -> int:
    # Rough English heuristic: ~4 characters per token. Round up.
    return (len(text) + 3) // 4


def _build_counter() -> Callable[[str], int]:
    tokenizer_path = resource_path("tokenizer.json")
    if not tokenizer_path.exists():
        logger.info(
            "tokenizer.json not found at %s; using char-based estimate",
            tokenizer_path,
        )
        return _char_estimate

    try:
        from tokenizers import Tokenizer
    except ImportError:
        logger.info("tokenizers package not installed; using char-based estimate")
        return _char_estimate

    tok = Tokenizer.from_file(str(tokenizer_path))
    return lambda text: len(tok.encode(text).ids)


def count_tokens(text: str) -> int:
    """Return an integer token count for `text`."""
    global _COUNT_TOKENS
    if _COUNT_TOKENS is None:
        _COUNT_TOKENS = _build_counter()
    return _COUNT_TOKENS(text)
