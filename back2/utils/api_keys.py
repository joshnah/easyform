"""Read provider API keys from the legacy `~/EasyForm/api_keys.json` file.

The Electron frontend's API Keys modal writes here (see
`front/src/helpers/ipc/file/file-listener.ts`). The legacy `back/llm_client.py`
also reads it. This module lets back2 providers fall back to it when the
expected env var (e.g. `OPENAI_API_KEY`) isn't set, so users who only set
their key via the UI don't need to re-enter it.
"""

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def _appdata_dir() -> str:
    """Mirror back/llm_client.get_appdata_dir without importing back/."""
    appdata = os.getenv("APPDATA") or os.path.expanduser("~")
    return os.path.join(appdata, "EasyForm")


def api_keys_path() -> str:
    """Absolute path to api_keys.json (does not create it)."""
    return os.path.join(_appdata_dir(), "api_keys.json")


def get_active_api_key(provider: str) -> Optional[str]:
    """Return the saved API key for `provider`, or None if absent.

    File schema (matches the legacy back/llm_client and the Electron writer):

        [
          {"provider": "openai", "key": "sk-..."},
          {"provider": "groq",   "key": "gsk_..."}
        ]
    """
    path = api_keys_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            entries = json.load(f)
    except Exception as e:
        logger.warning("Failed to read %s: %s", path, e)
        return None

    if not isinstance(entries, list):
        return None
    for entry in entries:
        if isinstance(entry, dict) and entry.get("provider") == provider:
            key = entry.get("key")
            if isinstance(key, str) and key:
                return key
    return None
