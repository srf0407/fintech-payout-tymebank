from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    google_id: str
    email: str
    name: Optional[str] = None
    picture_url: Optional[str] = None
    created_at: datetime


class UserCreate(BaseModel):
    model_config = ConfigDict(strict=True)

    google_id: str
    email: EmailStr
    name: Optional[str] = None
    picture_url: Optional[str] = None
