"""Authentication schemas."""

from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, Union


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_id: Optional[str] = None


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: Optional[str] = "member"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Union[UUID, str]
    tenant_id: Optional[Union[UUID, str]] = None
    email: EmailStr
    role: str
    is_superadmin: bool
    is_active: bool


class LoginResponse(BaseModel):
    access_token: str
    user: UserResponse
