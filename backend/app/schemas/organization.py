import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from app.models.organization import OrgStatus


class OrganizationCreate(BaseModel):
    """Payload to register a new licensed Chit Fund Company."""
    name: str = Field(..., min_length=2, max_length=150)
    registration_number: str = Field(..., min_length=2, max_length=100)
    tax_id: Optional[str] = Field(None, max_length=50)
    state_registration_details: Optional[str] = None
    status: OrgStatus = OrgStatus.ACTIVE


class OrganizationUpdate(BaseModel):
    """Payload to update organization metadata or active status."""
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    tax_id: Optional[str] = Field(None, max_length=50)
    state_registration_details: Optional[str] = None
    status: Optional[OrgStatus] = None


class OrganizationResponse(BaseModel):
    """Public representation of an Organization entity."""
    id: uuid.UUID
    name: str
    registration_number: str
    tax_id: Optional[str]
    state_registration_details: Optional[str]
    status: OrgStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
