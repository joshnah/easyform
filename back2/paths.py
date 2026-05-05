"""Resolve paths to back2 resources (tokenizer.json, config.json).

Works whether running from source (CWD-independent) or inside a PyInstaller
bundle (where files live under sys._MEIPASS).
"""

import os
import sys
from pathlib import Path


def _bundle_root() -> Path:
    """Return the directory the code lives in.

    Inside a PyInstaller bundle that's `sys._MEIPASS`. Otherwise it's the
    directory of this file (i.e. the back2 package directory).
    """
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            # Try the back2 subdirectory first (preserved package layout)
            back2_in_bundle = Path(meipass) / "back2"
            if back2_in_bundle.exists():
                return back2_in_bundle
            return Path(meipass)
    return Path(__file__).resolve().parent


def resource_path(name: str) -> Path:
    """Resolve a file shipped alongside the back2 package."""
    return _bundle_root() / name
