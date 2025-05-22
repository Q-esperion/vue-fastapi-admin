from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class TenantBase(BaseModel):
    name: str
    schema_name: str
    is_active: bool = True
    description: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None


class TenantCreate(TenantBase):
    owner_id: Optional[int] = None


class TenantUpdate(TenantBase):
    owner_id: Optional[int] = None


class TenantInDB(TenantBase):
    id: int
    owner_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True 