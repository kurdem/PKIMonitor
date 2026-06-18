"""Application configuration.

All settings can be overridden via environment variables or a ``.env`` file.
List-style values (CORS origins, alert thresholds, mail recipients) are stored
as plain comma-separated strings to avoid the JSON-parsing gotcha of
pydantic-settings, and exposed as parsed lists through properties.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Read a .env from the current working dir AND from the repository root,
        # so it works whether you run uvicorn from ./ or ./backend.
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- General ----------------------------------------------------------
    app_name: str = "PKIMonitor"
    debug: bool = False
    log_level: str = "INFO"

    # ---- Database ---------------------------------------------------------
    # e.g. sqlite:///./data/pkimonitor.db  or  postgresql+psycopg://user:pw@host/db
    database_url: str = "sqlite:///./data/pkimonitor.db"

    # ---- API security -----------------------------------------------------
    # If set, write operations (POST/PUT/DELETE) require header `X-API-Key`.
    api_key: str | None = None
    # Comma separated list of allowed CORS origins.
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://localhost:8080"

    # ---- Scheduler --------------------------------------------------------
    monitor_interval_hours: int = 6      # how often URL monitors are checked
    alert_interval_hours: int = 24       # how often alert evaluation runs
    run_checks_on_startup: bool = False  # run an initial monitor sweep at boot
    ssl_timeout_seconds: int = 10

    # ---- Alert thresholds (days before expiry), comma separated -----------
    alert_thresholds: str = "60,30,7"

    # ---- SMTP / email -----------------------------------------------------
    smtp_enabled: bool = False
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    smtp_from: str = "pkimonitor@example.com"
    smtp_to: str = ""  # comma separated recipients

    # ---- Webhook (Slack / Teams / generic) --------------------------------
    webhook_enabled: bool = False
    webhook_url: str | None = None
    webhook_type: str = "slack"  # slack | teams | generic

    # An empty env value (e.g. `API_KEY=` in .env) arrives as "" not None.
    # Normalize blanks to None so that "leave empty to disable auth" holds.
    @field_validator("api_key", "smtp_user", "smtp_password", "webhook_url", mode="before")
    @classmethod
    def _blank_to_none(cls, value):
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    # ---- Parsed list helpers ---------------------------------------------
    @staticmethod
    def _split(value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return self._split(self.cors_origins)

    @property
    def alert_threshold_list(self) -> list[int]:
        return sorted({int(x) for x in self._split(self.alert_thresholds)}, reverse=True)

    @property
    def smtp_to_list(self) -> list[str]:
        return self._split(self.smtp_to)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
