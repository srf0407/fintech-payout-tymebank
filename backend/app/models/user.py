from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from ..db.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    google_id = Column(String(64), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=True)
    picture_url = Column(String(500), nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    
    payouts = relationship("Payout", back_populates="user", cascade="all, delete-orphan", lazy="select")
