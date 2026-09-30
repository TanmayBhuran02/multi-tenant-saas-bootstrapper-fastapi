"""Phase 1 — Config tests."""

import os
import pytest

from multi_tenant_bootstrapper.config import (
    BootstrapperConfig,
    get_config,
    set_config,
)


class TestBootstrapperConfigDefaults:
    """Test default configuration values."""

    def test_default_config_values(self, monkeypatch):
        # Clear test env vars to test actual defaults
        for key in list(os.environ):
            if key.startswith("SAAS_"):
                monkeypatch.delenv(key, raising=False)
        cfg = BootstrapperConfig(
            _env_file=None,  # Don't read .env for this test
        )
        assert cfg.SECRET_KEY == "dev-secret-key-change-in-prod"
        assert cfg.DEBUG is True
        assert "postgresql+asyncpg://" in cfg.DATABASE_URL
        assert cfg.SQLALCHEMY_ECHO is False
        assert cfg.JWT_ALGORITHM == "HS256"
        assert cfg.JWT_ACCESS_TOKEN_EXPIRES == 86400

    def test_cors_origins_default(self):
        cfg = BootstrapperConfig(_env_file=None)
        assert cfg.CORS_ORIGINS == ["http://localhost:5173"]

    def test_optional_plan_overrides_none_by_default(self):
        cfg = BootstrapperConfig(_env_file=None)
        assert cfg.PLAN_FLAGS is None
        assert cfg.PLAN_LIMITS is None
        assert cfg.PLAN_FEATURES is None


class TestBootstrapperConfigEnv:
    """Test configuration from environment variables."""

    def test_config_from_env(self, monkeypatch):
        monkeypatch.setenv("SAAS_SECRET_KEY", "from-env-secret")
        monkeypatch.setenv("SAAS_DEBUG", "false")
        cfg = BootstrapperConfig(_env_file=None)
        assert cfg.SECRET_KEY == "from-env-secret"
        assert cfg.DEBUG is False


class TestAsyncDatabaseUrl:
    """Test get_async_database_url conversion logic."""

    def test_get_async_database_url_already_async(self):
        cfg = BootstrapperConfig(
            DATABASE_URL="postgresql+asyncpg://user:pass@host/db",
            _env_file=None,
        )
        assert cfg.get_async_database_url() == "postgresql+asyncpg://user:pass@host/db"

    def test_get_async_database_url_converts_sync(self):
        cfg = BootstrapperConfig(
            DATABASE_URL="postgresql://user:pass@host/db",
            _env_file=None,
        )
        assert cfg.get_async_database_url() == "postgresql+asyncpg://user:pass@host/db"


class TestConfigSingleton:
    """Test the global config singleton behavior."""

    def test_config_singleton_get_set(self):
        cfg = BootstrapperConfig(
            SECRET_KEY="singleton-test",
            _env_file=None,
        )
        set_config(cfg)
        retrieved = get_config()
        assert retrieved.SECRET_KEY == "singleton-test"
