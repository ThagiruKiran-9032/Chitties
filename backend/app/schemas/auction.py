import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.auction import AuctionStatus


class BidCreate(BaseModel):
    """Payload to place a reverse discount bid in an active auction."""
    bid_discount_amount: Decimal = Field(
        ...,
        gt=0,
        description="The discount amount the subscriber is willing to forego from the chit pot.",
    )
    chit_membership_id: Optional[uuid.UUID] = Field(
        None,
        description="Optional membership ID. If omitted, inferred from the authenticated user's ticket in the group.",
    )


class BidResponse(BaseModel):
    """Individual bid record returned in lists or real-time broadcast."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    auction_id: uuid.UUID
    chit_membership_id: uuid.UUID
    ticket_number: Optional[int] = None
    bidder_name: Optional[str] = None
    bid_discount_amount: Decimal
    timestamp: datetime
    is_valid: bool = True


class AuctionSummaryResponse(BaseModel):
    """High-level summary of an auction round."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chit_group_id: uuid.UUID
    month_number: int
    scheduled_at: datetime
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    status: AuctionStatus
    is_foreman_month: bool
    winning_membership_id: Optional[uuid.UUID] = None
    winning_ticket_number: Optional[int] = None
    winning_member_name: Optional[str] = None
    winning_bid_discount: Decimal
    foreman_commission: Decimal
    total_dividend_pool: Decimal
    dividend_per_ticket: Decimal
    net_payable_installment: Decimal
    current_highest_bid: Optional[Decimal] = None


class AuctionDetailResponse(AuctionSummaryResponse):
    """Detailed view of an auction for the live room and audit view."""
    group_code: str
    total_value: Decimal
    duration_months: int
    monthly_installment: Decimal
    min_bid_discount: Decimal
    max_bid_discount: Decimal
    user_membership_id: Optional[uuid.UUID] = None
    user_ticket_number: Optional[int] = None
    user_is_prized: bool = False
    recent_bids: List[BidResponse] = []


class AuctionCloseResponse(BaseModel):
    """Result returned when an auction session is closed and settled."""
    auction_id: uuid.UUID
    month_number: int
    winner_membership_id: Optional[uuid.UUID] = None
    winner_ticket_number: Optional[int] = None
    winner_name: Optional[str] = None
    winning_bid_discount: Decimal
    prize_amount: Decimal
    foreman_commission: Decimal
    total_dividend_pool: Decimal
    dividend_per_ticket: Decimal
    net_payable_installment: Decimal
    next_month_installments_generated: int = 0
