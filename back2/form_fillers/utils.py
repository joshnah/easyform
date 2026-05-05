# Reuse helper functions that were previously inline
def ensure_ext(path: str, ext: str) -> str:
    if not path.lower().endswith(f".{ext}"):
        return f"{path}.{ext}"
    return path

