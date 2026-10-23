import uuid
from datetime import date, time, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

from app.models.chit_group import ChitGroupStatus
from app.models.membership import MembershipStatus
from app.schemas.chit_scheme import ChitSchemeResponse


class ChitGroupCreate(BaseModel):
    """Payload to launch a new Chit Group circle."""
    branch_id: uuid.UUID
    scheme_id: uuid.UUID
    manager_id: Optional[uuid.UUID] = None
    group_code: str = Field(..., min_length=2, max_length=50)
    start_date: date
    end_date: date
    auction_day_of_month: int = Field(..., ge=1, le=28)
    auction_time: time


class ChitGroupAssignManagerRequest(BaseModel):
    """Payload to assign a Manager to a Chit Group."""
    manager_id: uuid.UUID


class ChitGroupStatusUpdate(BaseModel):
    """Payload to transition chit group status."""
    status: ChitGroupStatus


class EnrollmentRequest(BaseModel):
    """Payload to assign a subscriber to a ticket in a chit group."""
    user_id: uuid.UUID
    ticket_number: int = Field(..., ge=1)


class ChitMembershipResponse(BaseModel):
    """Representation of an enrolled ticket."""
    id: uuid.UUID
    chit_group_id: uuid.UUID
    user_id: uuid.UUID
    ticket_number: int
    status: MembershipStatus
    enrolled_at: datetime
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ChitGroupResponse(BaseModel):
    """Representation of a Chit Group."""
    id: uuid.UUID
    organization_id: uuid.UUID
    branch_id: uuid.UUID
    scheme_id: uuid.UUID
    group_code: str
    start_date: date
    end_date: date
    current_month: int
    auction_day_of_month: int
    auction_time: time
    status: ChitGroupStatus
    created_at: datetime
    enrolled_count: int = 0
    total_capacity: int = 0
    manager_id: Optional[uuid.UUID] = None
    manager_name: Optional[str] = None
    scheme: Optional[ChitSchemeResponse] = None

    model_config = ConfigDict(from_attributes=True)
