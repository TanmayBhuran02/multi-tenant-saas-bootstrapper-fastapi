"""Admin panel schemas."""

from pydantic import BaseModel
from typing import List, Dict, Any


class PaginationInfo(BaseModel):
    page: int
    per_page: int
    total: int
    pages: int


class TenantListResponse(BaseModel):
    tenants: List[Dict[str, Any]]
    pagination: PaginationInfo


class GlobalMetricsResponse(BaseModel):
    metrics: Dict[str, Any]


class TenantMetricsResponse(BaseModel):
    tenant: Dict[str, Any]
    metrics: Dict[str, Any]
