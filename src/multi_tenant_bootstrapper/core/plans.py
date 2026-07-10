"""Plan definitions and resource limits.

The default ``PLAN_LIMITS`` and ``PLAN_FEATURES`` mappings can be
overridden by providing custom mappings via ``BootstrapperConfig``.
"""

from typing import Any

from multi_tenant_bootstrapper.config import get_config

# ── Default Plan Limits ──────────────────────────────────────────────────────

DEFAULT_PLAN_LIMITS: dict[str, dict[str, Any]] = {
    'free': {
        'users': 3,
        'api_calls': 1000,
        'storage_mb': 100,
        'projects': 1,
        'price_monthly': 0,
    },
    'starter': {
        'users': 10,
        'api_calls': 10000,
        'storage_mb': 1000,
        'projects': 5,
        'price_monthly': 29,
    },
    'pro': {
        'users': 50,
        'api_calls': 100000,
        'storage_mb': 10000,
        'projects': 25,
        'price_monthly': 99,
    },
    'enterprise': {
        'users': -1,  # unlimited
        'api_calls': -1,
        'storage_mb': -1,
        'projects': -1,
        'price_monthly': 299,
    },
}

# ── Default Plan Features (display labels) ───────────────────────────────────

DEFAULT_PLAN_FEATURES: dict[str, list[str]] = {
    'free': [
        'Basic Dashboard',
        'Community Support',
        'Up to 3 Users',
    ],
    'starter': [
        'Everything in Free',
        'CSV Export',
        'API Access',
        'Email Support',
        'Up to 10 Users',
    ],
    'pro': [
        'Everything in Starter',
        'Advanced Analytics',
        'Webhooks',
        'SSO Integration',
        'Priority Support',
        'Up to 50 Users',
    ],
    'enterprise': [
        'Everything in Pro',
        'Audit Logs',
        'Custom Domain',
        'Dedicated Support',
        'Unlimited Users',
        'SLA Guarantee',
    ],
}


def _get_limits() -> dict[str, dict[str, Any]]:
    """Return the active plan limits, respecting config overrides."""
    config = get_config()
    if config.PLAN_LIMITS is not None:
        return config.PLAN_LIMITS
    return DEFAULT_PLAN_LIMITS


def _get_features() -> dict[str, list[str]]:
    """Return the active plan features, respecting config overrides."""
    config = get_config()
    if config.PLAN_FEATURES is not None:
        return config.PLAN_FEATURES
    return DEFAULT_PLAN_FEATURES


def get_plan_limits(plan_name: str) -> dict[str, Any]:
    """Get resource limits for a plan."""
    limits = _get_limits()
    return limits.get(plan_name, limits.get('free', {}))


def get_plan_features(plan_name: str) -> list[str]:
    """Get feature list for a plan."""
    features = _get_features()
    return features.get(plan_name, features.get('free', []))


def get_all_plan_limits() -> dict[str, dict[str, Any]]:
    """Get limits for all plans."""
    return _get_limits()
