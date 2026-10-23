import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from app.models.organization import BranchStatus


class BranchCreate(BaseModel):
    """Payload to create an operational Branch."""
    branch_code: str = Field(..., min_length=2, max_length=30)
    name: str = Field(..., min_length=2, max_length=150)
    address: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=20)
    status: BranchStatus = BranchStatus.ACTIVE


class BranchUpdate(BaseModel):
    """Payload to update branch information."""
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    address: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=20)
    status: Optional[BranchStatus] = None


class BranchResponse(BaseModel):
    """Public representation of a Branch."""
    id: uuid.UUID
    organization_id: uuid.UUID
    branch_code: str
    name: str
    address: Optional[str]
    phone: Optional[str]
    status: BranchStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
