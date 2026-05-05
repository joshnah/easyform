"""Convenience entry-point to launch the FastAPI backend on port 8000.

Run `python -m back2.server` (or `python back2/server.py`) and visit
http://localhost:8000/docs for the interactive Swagger UI.
"""

import os
import sys

import uvicorn

# PyInstaller: when frozen, _MEIPASS holds the bundle root.
if getattr(sys, "frozen", False):
    bundle_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, bundle_dir)


if __name__ == "__main__":
    from back2.api import app

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
