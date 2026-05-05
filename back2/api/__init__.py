"""FastAPI app composition.

`from back2.api import app` resolves here. The app mounts two routers:

- `native` — the recommended document-first endpoints.
- `compat` — legacy endpoints used by the existing frontend; lazily delegate
  to the `back/` package for parity.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from back2.api.compat import router as compat_router
from back2.api.native import router as native_router

logger = logging.getLogger(__name__)

app = FastAPI(title="EasyForm Backend API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(native_router)
app.include_router(compat_router)


@app.on_event("startup")
def _prewarm_tokenizer() -> None:
    """Load the HuggingFace tokenizer eagerly so the first /document/analyze
    or /context/search request doesn't pay the ~9 MB JSON parse on the
    request thread. Failures are non-fatal — `count_tokens` falls back to a
    char-based estimate.
    """
    try:
        from back2.utils.tokenization import count_tokens

        count_tokens("warmup")
        logger.info("tokenizer pre-warmed")
    except Exception as e:
        logger.warning("tokenizer pre-warm failed: %s (using char fallback)", e)


__all__ = ["app"]
