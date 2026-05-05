"""FastAPI app composition.

`from back2.api import app` resolves here. The app mounts two routers:

- `native` — the recommended document-first endpoints.
- `compat` — legacy endpoints used by the existing frontend; lazily delegate
  to the `back/` package for parity.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from back2.api.compat import router as compat_router
from back2.api.native import router as native_router

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

__all__ = ["app"]
