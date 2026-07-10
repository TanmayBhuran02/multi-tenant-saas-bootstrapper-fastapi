"""Bootstrapper configuration using Pydantic Settings.

All settings can be provided via:
1. Direct instantiation: ``BootstrapperConfig(DATABASE_URL="...")``
2. Environment variables with the ``SAAS_`` prefix: ``SAAS_DATABASE_URL=...``
3. A ``.env`` file (auto-loaded)

Developers can also override plan definitions (flags, limits, features)
by passing custom dicts to the config, which will replace the defaults.
"""

from __future__ import annotations

import os
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BootstrapperConfig(BaseSettings):
    """Configuration for the Multi-Tenant SaaS Bootstrapper.

    All fields have sensible defaults for local development.
    Override them via env vars (prefixed ``SAAS_``) or by passing
    values directly to the constructor.
    """

    model_config = SettingsConfigDict(
        env_prefix="SAAS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────
    SECRET_KEY: str = "dev-secret-key-change-in-prod"
    DEBUG: bool = True

    # ── Database ─────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://saas:saas@localhost:5432/saas_bootstrapper",
        description="Async SQLAlchemy database URL. Use postgresql+asyncpg:// format.",
    )
    SQLALCHEMY_ECHO: bool = False

    # ── JWT ──────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "jwt-dev-secret-change-in-prod"
    JWT_ACCESS_TOKEN_EXPIRES: int = Field(
        default=86400,
        description="JWT access token expiry in seconds (default: 24h).",
    )
    JWT_ALGORITHM: str = "HS256"

    # ── Superadmin ───────────────────────────────────────────────────────
    SUPERADMIN_SECRET: str = "superadmin-dev-secret"

    # ── CORS ─────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:5173"],
        description="Allowed CORS origins.",
    )

    # ── Middleware ────────────────────────────────────────────────────────
    SKIP_HOSTS_PATTERN: str | None = Field(
        default=None,
        description=(
            "Custom regex pattern for hosts the tenant middleware should skip. "
            "Defaults to localhost/IP addresses when None."
        ),
    )

    # ── Extensibility: Plan & Flag Overrides ─────────────────────────────
    PLAN_FLAGS: dict[str, list[str]] | None = Field(
        default=None,
        description=(
            "Override the default PLAN_FLAGS mapping. Keys should be PlanType "
            "values ('free', 'starter', 'pro', 'enterprise')."
        ),
    )
    PLAN_LIMITS: dict[str, dict[str, Any]] | None = Field(
        default=None,
        description="Override the default PLAN_LIMITS mapping.",
    )
    PLAN_FEATURES: dict[str, list[str]] | None = Field(
        default=None,
        description="Override the default PLAN_FEATURES mapping.",
    )

    def get_async_database_url(self) -> str:
        """Return the database URL with the async driver.

        Automatically converts ``postgresql://`` to
        ``postgresql+asyncpg://`` if needed.
        """
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


# ── Singleton ────────────────────────────────────────────────────────────────
_config: BootstrapperConfig | None = None


def get_config() -> BootstrapperConfig:
    """Return the current global config, creating a default one if needed."""
    global _config
    if _config is None:
        _config = BootstrapperConfig()
    return _config


def set_config(config: BootstrapperConfig) -> None:
    """Set the global config singleton (called by ``create_app``)."""
    global _config
    _config = config
