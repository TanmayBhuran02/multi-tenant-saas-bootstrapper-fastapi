"""Phase 4b — Plans tests (plan limits, features, config overrides)."""

import pytest

from multi_tenant_bootstrapper.config import BootstrapperConfig, set_config, get_config
from multi_tenant_bootstrapper.core.plans import (
    get_plan_limits,
    get_plan_features,
    get_all_plan_limits,
    DEFAULT_PLAN_LIMITS,
    DEFAULT_PLAN_FEATURES,
)


class TestGetPlanLimits:

    def test_get_plan_limits_free(self):
        limits = get_plan_limits("free")
        assert limits["users"] == 3
        assert limits["api_calls"] == 1000
        assert limits["price_monthly"] == 0

    def test_get_plan_limits_enterprise(self):
        limits = get_plan_limits("enterprise")
        assert limits["users"] == -1  # unlimited
        assert limits["price_monthly"] == 299

    def test_get_plan_limits_all_plans(self):
        for plan in ("free", "starter", "pro", "enterprise"):
            limits = get_plan_limits(plan)
            assert "users" in limits
            assert "api_calls" in limits

    def test_get_plan_limits_unknown_plan_fallback(self):
        limits = get_plan_limits("nonexistent")
        # Should fall back to free
        assert limits == DEFAULT_PLAN_LIMITS["free"]


class TestGetPlanFeatures:

    def test_get_plan_features_free(self):
        features = get_plan_features("free")
        assert "Basic Dashboard" in features

    def test_get_plan_features_enterprise(self):
        features = get_plan_features("enterprise")
        assert "Audit Logs" in features
        assert "SLA Guarantee" in features

    def test_get_plan_features_unknown_plan_fallback(self):
        features = get_plan_features("nonexistent")
        assert features == DEFAULT_PLAN_FEATURES["free"]


class TestGetAllPlanLimits:

    def test_get_all_plan_limits(self):
        all_limits = get_all_plan_limits()
        assert set(all_limits.keys()) == {"free", "starter", "pro", "enterprise"}


class TestConfigOverrides:

    def test_config_override_plan_limits(self):
        original_config = get_config()
        try:
            custom_limits = {"free": {"users": 100, "api_calls": 99999}}
            cfg = BootstrapperConfig(
                PLAN_LIMITS=custom_limits,
                _env_file=None,
            )
            set_config(cfg)
            limits = get_plan_limits("free")
            assert limits["users"] == 100
            assert limits["api_calls"] == 99999
        finally:
            set_config(original_config)

    def test_config_override_plan_features(self):
        original_config = get_config()
        try:
            custom_features = {"free": ["Custom Feature"]}
            cfg = BootstrapperConfig(
                PLAN_FEATURES=custom_features,
                _env_file=None,
            )
            set_config(cfg)
            features = get_plan_features("free")
            assert features == ["Custom Feature"]
        finally:
            set_config(original_config)
