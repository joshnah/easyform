import uvicorn


if __name__ == "__main__":
    """Convenience entry-point to launch the FastAPI backend.

    Run `python -m back.server` (or `python back/server.py`) and then visit
    http://localhost:8000/docs for the interactive Swagger UI or
    http://localhost:8000/redoc for ReDoc. The OpenAPI JSON is available at
    http://localhost:8000/openapi.json.
    """
    # Import here to avoid side-effects if the module is imported elsewhere.
    from .api import app  # noqa: WPS433 – internal import for runtime

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True) 