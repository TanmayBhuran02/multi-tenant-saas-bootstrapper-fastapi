"""Plan definitions and resource limits."""

PLAN_LIMITS = {
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

PLAN_FEATURES = {
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


def get_plan_limits(plan_name):
    """Get resource limits for a plan."""
    return PLAN_LIMITS.get(plan_name, PLAN_LIMITS['free'])


def get_plan_features(plan_name):
    """Get feature list for a plan."""
    return PLAN_FEATURES.get(plan_name, PLAN_FEATURES['free'])
