"""Resolve paths to back2 resources (tokenizer.json, config.json).

Works whether running from source (CWD-independent) or inside a PyInstaller
bundle (where files live under sys._MEIPASS).
"""

import os
import sys
from pathlib import Path


def _bundle_root() -> Path:
    """Return the back2 package directory.

    Inside a PyInstaller bundle that's `sys._MEIPASS/back2/` (or `sys._MEIPASS`
    flat). In source it's the parent of `back2/utils/` — i.e. `back2/` itself.
    """
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            back2_in_bundle = Path(meipass) / "back2"
            if back2_in_bundle.exists():
                return back2_in_bundle
            return Path(meipass)
    # Source layout: this file is back2/utils/paths.py, so go up one level.
    return Path(__file__).resolve().parent.parent


def resource_path(name: str) -> Path:
    """Resolve a file shipped alongside the back2 package."""
    return _bundle_root() / name
