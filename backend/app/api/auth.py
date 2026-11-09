from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from app.api.deps import COOKIE, Config, CurrentUser, Session
from app.core.security import create_access_token
from app.schemas import LoginIn, MeOut
from app.core.config import Settings
from app.db.models import User
from app.services.users import authenticate, owner

router = APIRouter()


def _set_session_cookie(response: Response, user: User, cfg: Settings) -> None:
    response.set_cookie(
        COOKIE,
        create_access_token(str(user.id), cfg.secret_key, cfg.session_ttl),
        max_age=int(cfg.session_ttl.total_seconds()),
        httponly=True, samesite="strict", secure=cfg.cookie_secure, path="/api",
    )


@router.post("/auth/login", response_model=MeOut)
async def login(body: LoginIn, request: Request, response: Response, session: Session, cfg: Config) -> MeOut:
    limiter = request.app.state.login_limiter
    keys = (f"ip:{request.client.host if request.client else '?'}", f"email:{body.email.strip().lower()}")
    # Evaluate every key (no short-circuit) so each attempt is counted against both.
    if not all([limiter.hit(k) for k in keys]):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts, try again later")
    user = await authenticate(session, body.email, body.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    for k in keys:
        limiter.reset(k)
    _set_session_cookie(response, user, cfg)
    return MeOut(email=user.email)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    response.delete_cookie(COOKIE, path="/api")


@router.get("/me", response_model=MeOut)
async def me(user: CurrentUser, cfg: Config) -> MeOut:
    return MeOut(email=user.email, desktop=cfg.desktop_token is not None)


@router.get("/auth/desktop", include_in_schema=False)
async def desktop_session(token: str, session: Session, cfg: Config) -> Response:
    """Standalone app only: the window presents the per-launch token and gets a session, no password."""
    if cfg.desktop_token is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    if not secrets.compare_digest(token.encode(), cfg.desktop_token.encode()):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid token")
    user = await owner(session)
    if user is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Not ready")
    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    _set_session_cookie(response, user, cfg)
    return response
