"""Read/write helpers for `<context_dir>/context_data.json`.

Used by the legacy `/context/{read,add,update,delete}` compat endpoints — the
file I/O is identical between them, only the dict mutation differs.
"""

import json
import os


def _path(context_dir: str) -> str:
    return os.path.join(context_dir, "context_data.json")


def read(context_dir: str) -> dict:
    """Read context_data.json. Returns `{}` if the file doesn't exist."""
    path = _path(context_dir)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write(context_dir: str, data: dict) -> None:
    """Write context_data.json, creating the directory if needed."""
    os.makedirs(context_dir, exist_ok=True)
    with open(_path(context_dir), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
