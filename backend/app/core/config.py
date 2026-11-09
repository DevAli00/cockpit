from datetime import timedelta
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from the environment. Nothing sensitive has a default."""

    model_config = SettingsConfigDict(env_prefix="COCKPIT_", env_file=".env", extra="ignore")

    database_url: str
    secret_key: str = Field(min_length=32)
    admin_email: str = Field(min_length=3)
    admin_password: str = Field(min_length=10)
    cookie_secure: bool = False  # set true when served over HTTPS
    session_hours: int = Field(default=24 * 14, ge=1)
    login_attempts: int = Field(default=5, ge=1)
    login_window_s: int = Field(default=300, ge=1)
    # Standalone desktop app only (set by the launcher, never on a server):
    desktop_token: str | None = Field(default=None, min_length=32)  # per-launch secret that opens a session
    static_dir: Path | None = None  # built web app to serve from this process
    auto_schema: bool = False  # create/upgrade tables at startup instead of Alembic

    @property
    def session_ttl(self) -> timedelta:
        return timedelta(hours=self.session_hours)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # values come from the environment
