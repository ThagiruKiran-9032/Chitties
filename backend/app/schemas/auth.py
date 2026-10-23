import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.models.user import UserRole, KYCStatus


class UserRegisterRequest(BaseModel):
    """Payload for subscriber or staff account self-registration."""
    full_name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20)
    password: str = Field(..., min_length=8, max_length=100)
    organization_id: Optional[uuid.UUID] = None
    branch_id: Optional[uuid.UUID] = None


class UserLoginRequest(BaseModel):
    """Payload for user authentication."""
    email: EmailStr
    password: str = Field(..., min_length=1)


class UserProfileResponse(BaseModel):
    """Public user identity and role representation."""
    id: uuid.UUID
    organization_id: Optional[uuid.UUID]
    branch_id: Optional[uuid.UUID]
    full_name: str
    email: str
    phone: str
    role: UserRole
    kyc_status: KYCStatus
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """JWT bearer token and authenticated user metadata."""
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: UserProfileResponse


class EmailVerifyRequest(BaseModel):
    """Payload to confirm email address with timed token."""
    token: str


class ForgotPasswordRequest(BaseModel):
    """Payload to initiate password recovery via SMTP."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Payload to finalize password reset."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


class MessageResponse(BaseModel):
    """Standardized API response for operational feedback."""
    message: str
    status: str = "success"
    email_delivered: Optional[bool] = None
