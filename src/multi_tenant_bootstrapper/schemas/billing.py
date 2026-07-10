"""Billing and plan schemas."""

from pydantic import BaseModel
from typing import Dict, Any, List


class UpgradePlanRequest(BaseModel):
    tenant_id: str
    new_plan: str


class PlanResponse(BaseModel):
    plan: str
    limits: Dict[str, Any]
    features: List[str]
    usage: Dict[str, int]
    all_plans: Dict[str, Any]


class UpgradePlanResponse(BaseModel):
    tenant: Dict[str, Any]
    old_plan: str
    new_plan: str
    new_flags_enabled: List[str]
