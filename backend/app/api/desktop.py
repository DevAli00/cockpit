"""Things only the standalone desktop app can do: they need a native window."""
from __future__ import annotations

import datetime as dt
from typing import Protocol

from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.concurrency import run_in_threadpool

from app.api.deps import Session, current_user
from app.services import backup


class DesktopBridge(Protocol):
    """Implemented by the desktop launcher. Called from a worker thread; may block on a dialog."""

    def save_text(self, suggested_name: str, content: str) -> bool:
        """Ask the user where to save `content`. False when they cancel."""
        ...


router = APIRouter(dependencies=[Depends(current_user)])


@router.post("/desktop/backup-file")
async def save_backup_file(request: Request, s: Session) -> dict[str, bool]:
    """Write the full backup to a file the user picks in a native dialog.

    Embedded web views do not reliably support downloads, and the page gets no native API:
    the server builds the file itself, so this can only ever write the user's own backup.
    """
    bridge: DesktopBridge | None = getattr(request.app.state, "desktop_bridge", None)
    if bridge is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    content = (await backup.export_all(s)).model_dump_json(indent=2)
    name = f"cockpit-backup-{dt.date.today():%Y-%m-%d}.json"
    return {"saved": await run_in_threadpool(bridge.save_text, name, content)}
