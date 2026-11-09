from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api import auth, desktop, life, money, resources
from app.api.desktop import DesktopBridge
from app.api.frontend import CSP, mount_frontend
from app.core.config import Settings, get_settings
from app.core.ratelimit import SlidingWindowLimiter
from app.db.bootstrap import ensure_schema
from app.db.session import make_engine, make_session_factory
from app.services.errors import InvalidError, NotFoundError
from app.services.users import ensure_owner

log = logging.getLogger("cockpit")


def create_app(
    settings: Settings | None = None, engine: AsyncEngine | None = None,
    desktop_bridge: DesktopBridge | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    engine = engine or make_engine(settings.database_url)
    factory = make_session_factory(engine)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if settings.auto_schema:
            await ensure_schema(engine)
        async with factory() as s:
            await ensure_owner(s, settings.admin_email, settings.admin_password)
        yield
        await engine.dispose()

    # No interactive docs in production: they are not needed on a private network.
    app = FastAPI(title="Cockpit", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.session_factory = factory
    app.state.desktop_bridge = desktop_bridge
    app.state.login_limiter = SlidingWindowLimiter(settings.login_attempts, settings.login_window_s)

    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if settings.static_dir is not None:
            response.headers["Content-Security-Policy"] = CSP
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(NotFoundError)
    async def _not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.exception_handler(InvalidError)
    async def _invalid(_: Request, exc: InvalidError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=422)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse({"detail": "Internal server error"}, status_code=500)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth.router, prefix="/api")
    app.include_router(resources.router, prefix="/api")
    app.include_router(life.router, prefix="/api")
    app.include_router(money.router, prefix="/api")
    app.include_router(desktop.router, prefix="/api")
    if settings.desktop_token is not None:
        # Local-only app: refuse requests that arrive under another host name (DNS rebinding).
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    if settings.static_dir is not None:
        mount_frontend(app, settings.static_dir)
    return app
