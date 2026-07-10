"""Tenant provisioning and config schemas."""

from pydantic import BaseModel, EmailStr
from typing import Optional, Any


class ProvisionTenantRequest(BaseModel):
    display_name: str
    subdomain: str
    plan: Optional[str] = 'free'
    owner_email: EmailStr
    owner_password: str


class TenantConfigUpsert(BaseModel):
    key: str
    value: Optional[Any] = None
    is_secret: Optional[bool] = False


class TenantResponse(BaseModel):
    id: str
    slug: str
    subdomain: str
    display_name: str
    plan: str
    status: str

    class Config:
        from_attributes = True


class ProvisionTenantResponse(BaseModel):
    tenant: TenantResponse
    owner: dict
