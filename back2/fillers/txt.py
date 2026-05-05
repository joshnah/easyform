import os

from back2.fillers.base import BaseFiller, FillResult, ensure_ext


class TxtFiller(BaseFiller):
    def _save(self, fill_result: FillResult, output_path: str) -> None:
        out = ensure_ext(output_path, "txt")
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(fill_result.filled_text)
