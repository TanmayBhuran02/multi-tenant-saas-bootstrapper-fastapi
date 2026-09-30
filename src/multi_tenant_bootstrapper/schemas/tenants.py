"""Tenant provisioning and config schemas."""

from uuid import UUID
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, Any, Union


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
    model_config = ConfigDict(from_attributes=True)

    id: Union[UUID, str]
    slug: str
    subdomain: str
    display_name: str
    plan: str
    status: str


class ProvisionTenantResponse(BaseModel):
    tenant: TenantResponse
    owner: dict
