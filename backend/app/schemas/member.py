import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.models.user import UserRole, KYCStatus


class MemberCreate(BaseModel):
    """Payload for staff/admin to onboard a subscriber or staff member."""
    full_name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20)
    password: str = Field(..., min_length=8, max_length=100)
    role: UserRole = UserRole.SUBSCRIBER
    branch_id: Optional[uuid.UUID] = None
    kyc_document_type: Optional[str] = Field(None, max_length=50)
    kyc_document_number: Optional[str] = Field(None, max_length=100)


class MemberUpdate(BaseModel):
    """Payload to modify member profile or active state."""
    full_name: Optional[str] = Field(None, min_length=2, max_length=150)
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    branch_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None


class KYCSubmission(BaseModel):
    """Payload for subscriber or staff to submit identity documents for compliance."""
    kyc_document_type: str = Field(..., min_length=2, max_length=50)
    kyc_document_number: str = Field(..., min_length=2, max_length=100)


class KYCStatusUpdate(BaseModel):
    """Payload for Branch Manager or Org Admin to verify/reject KYC."""
    status: KYCStatus
    remarks: Optional[str] = None


class MemberResponse(BaseModel):
    """Public representation of a Member."""
    id: uuid.UUID
    organization_id: Optional[uuid.UUID]
    branch_id: Optional[uuid.UUID]
    full_name: str
    email: str
    phone: str
    role: UserRole
    kyc_status: KYCStatus
    kyc_document_type: Optional[str]
    kyc_document_number: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
