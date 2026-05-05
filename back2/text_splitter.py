"""Recursive character-based text splitter.

Stand-in for langchain's `RecursiveCharacterTextSplitter`. We only need the
split-then-pack-with-overlap behavior; everything else langchain ships with
(loaders, vector stores, chains) is dead weight on an edge device.
"""

from typing import List

DEFAULT_SEPARATORS = ("\n\n", "\n", ". ", " ")


def split_text(
    text: str,
    chunk_size: int,
    chunk_overlap: int = 50,
) -> List[str]:
    """Split `text` into chunks of at most `chunk_size` characters.

    Adjacent chunks share `chunk_overlap` characters of context. Splits prefer
    natural boundaries (paragraph break > newline > sentence > word). If no
    boundary is found in the second half of the window, falls back to a hard
    character cut.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be in [0, chunk_size)")

    if len(text) <= chunk_size:
        return [text]

    chunks: List[str] = []
    start = 0
    n = len(text)
    min_break = chunk_size // 2  # only honor a separator if it's past the midpoint

    while start < n:
        end = start + chunk_size
        if end >= n:
            chunks.append(text[start:])
            break

        # Look for a natural boundary in [start + min_break, end].
        cut = end
        for sep in DEFAULT_SEPARATORS:
            i = text.rfind(sep, start + min_break, end)
            if i != -1:
                cut = i + len(sep)
                break

        chunks.append(text[start:cut])
        start = max(cut - chunk_overlap, start + 1)

    return chunks
