"""Serves the built web app from the API process (standalone desktop app; nginx does it on a server)."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, Response

CSP = (
    "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
    "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)


def mount_frontend(app: FastAPI, static_dir: Path) -> None:
    """Register last: it catches every path the API did not."""
    root = static_dir.resolve()
    index = root / "index.html"

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str) -> Response:
        if path == "api" or path.startswith("api/"):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        candidate = (root / path).resolve()
        if path and candidate.is_relative_to(root) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index, media_type="text/html")  # client-side routes
