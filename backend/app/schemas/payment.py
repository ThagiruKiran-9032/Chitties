import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.installment import InstallmentStatus
from app.models.payment import PaymentMethod, PaymentStatus


class PaymentCreate(BaseModel):
    """Payload to record an installment payment with idempotency guarantee."""
    installment_id: uuid.UUID = Field(..., description="ID of the installment to settle.")
    amount: Decimal = Field(..., gt=0, description="Amount paid in INR.")
    payment_method: PaymentMethod = Field(..., description="Payment channel.")
    transaction_reference: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Unique transaction ID, UPI UTR, or client idempotency token.",
    )
    notes: Optional[str] = Field(None, max_length=500, description="Optional cashier or bank notes.")


class PaymentResponse(BaseModel):
    """Digital receipt and transaction record."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    chit_membership_id: uuid.UUID
    installment_id: uuid.UUID
    ticket_number: Optional[int] = None
    subscriber_name: Optional[str] = None
    group_code: Optional[str] = None
    month_number: Optional[int] = None
    amount_paid: Decimal
    payment_method: PaymentMethod
    transaction_reference: str
    receipt_number: str
    status: PaymentStatus
    recorded_by_name: Optional[str] = None
    notes: Optional[str] = None
    paid_at: datetime


class InstallmentDetailResponse(BaseModel):
    """Individual installment row including applied dividends, penalties, and payment history."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chit_group_id: uuid.UUID
    chit_membership_id: uuid.UUID
    ticket_number: int
    subscriber_name: str
    month_number: int
    due_date: date
    gross_amount: Decimal
    dividend_amount: Decimal
    penalty_amount: Decimal
    net_due_amount: Decimal
    paid_amount: Decimal
    remaining_balance: Decimal
    status: InstallmentStatus
    payments: List[PaymentResponse] = []


class MemberLedgerSummaryResponse(BaseModel):
    """Complete financial ledger statement for a subscriber's subscribed ticket."""
    chit_membership_id: uuid.UUID
    chit_group_id: uuid.UUID
    group_code: str
    ticket_number: int
    subscriber_name: str
    subscriber_email: str
    subscriber_phone: str
    total_gross_obligations: Decimal
    total_dividends_earned: Decimal
    total_penalties_applied: Decimal
    total_net_due: Decimal
    total_amount_paid: Decimal
    total_outstanding_balance: Decimal
    installments: List[InstallmentDetailResponse]


class PenaltyCreate(BaseModel):
    """Payload to apply an overdue late fee/penalty to an installment."""
    penalty_amount: Decimal = Field(..., gt=0, description="Penalty fee in INR.")
    reason: Optional[str] = Field(None, max_length=200, description="Audit reason for penalty.")
