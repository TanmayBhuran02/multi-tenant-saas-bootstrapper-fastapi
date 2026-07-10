"""Feature flag schemas."""

from pydantic import BaseModel
from typing import Optional, Any


class ToggleFlagRequest(BaseModel):
    enabled: bool
    tenant_id: Optional[str] = None
    payload: Optional[Any] = None
