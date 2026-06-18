"""Shared FastAPI dependencies (optional API-key auth)."""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from .config import settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Guard write operations with a simple shared API key.

    Auth is disabled entirely when ``API_KEY`` is not configured, which keeps
    local development frictionless while allowing it to be switched on in prod.
    """
    # Auth is disabled when no (non-blank) key is configured.
    if not settings.api_key:
        return
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
