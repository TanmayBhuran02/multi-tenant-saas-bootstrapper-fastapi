"""Phase 3 — Schema validation tests."""

import pytest
from pydantic import ValidationError

from multi_tenant_bootstrapper.schemas.auth import (
    LoginRequest, RegisterRequest, LoginResponse, UserResponse,
)
from multi_tenant_bootstrapper.schemas.tenants import (
    ProvisionTenantRequest, TenantConfigUpsert, TenantResponse,
)
from multi_tenant_bootstrapper.schemas.features import ToggleFlagRequest
from multi_tenant_bootstrapper.schemas.billing import (
    UpgradePlanRequest, PlanResponse, UpgradePlanResponse,
)


class TestLoginRequest:

    def test_login_request_valid(self):
        req = LoginRequest(email="user@example.com", password="pass123")
        assert req.email == "user@example.com"
        assert req.password == "pass123"
        assert req.tenant_id is None

    def test_login_request_invalid_email(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="not-an-email", password="pass123")


class TestRegisterRequest:

    def test_register_request_password_min_length(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(email="user@example.com", password="short")
        assert "min_length" in str(exc_info.value).lower() or "at least 8" in str(exc_info.value).lower()

    def test_register_request_default_role(self):
        req = RegisterRequest(email="user@example.com", password="password123")
        assert req.role == "member"

    def test_register_request_valid(self):
        req = RegisterRequest(
            email="user@example.com",
            password="password123",
            role="admin",
        )
        assert req.role == "admin"


class TestProvisionTenantRequest:

    def test_provision_tenant_request_valid(self):
        req = ProvisionTenantRequest(
            display_name="Acme Corp",
            subdomain="acme",
            owner_email="owner@acme.com",
            owner_password="strongpass123",
        )
        assert req.display_name == "Acme Corp"
        assert req.subdomain == "acme"

    def test_provision_tenant_request_default_plan(self):
        req = ProvisionTenantRequest(
            display_name="Acme Corp",
            subdomain="acme",
            owner_email="owner@acme.com",
            owner_password="strongpass123",
        )
        assert req.plan == "free"


class TestTenantConfigUpsert:

    def test_tenant_config_upsert_defaults(self):
        req = TenantConfigUpsert(key="theme")
        assert req.is_secret is False
        assert req.value is None


class TestToggleFlagRequest:

    def test_toggle_flag_request(self):
        req = ToggleFlagRequest(enabled=True)
        assert req.enabled is True
        assert req.tenant_id is None
        assert req.payload is None

    def test_toggle_flag_request_with_payload(self):
        req = ToggleFlagRequest(
            enabled=False,
            tenant_id="abc-123",
            payload={"rollout": 50},
        )
        assert req.enabled is False
        assert req.tenant_id == "abc-123"
        assert req.payload == {"rollout": 50}


class TestUpgradePlanRequest:

    def test_upgrade_plan_request(self):
        req = UpgradePlanRequest(tenant_id="tenant-1", new_plan="pro")
        assert req.tenant_id == "tenant-1"
        assert req.new_plan == "pro"


class TestPlanResponse:

    def test_plan_response_schema(self):
        resp = PlanResponse(
            plan="free",
            limits={"users": 3},
            features=["Basic Dashboard"],
            usage={"users": 1, "api_calls": 0},
            all_plans={"free": {"users": 3}},
        )
        assert resp.plan == "free"
        assert resp.limits["users"] == 3
        assert len(resp.features) == 1
