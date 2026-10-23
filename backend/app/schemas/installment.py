import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.installment import InstallmentStatus


class PaymentRecordResponse(BaseModel):
    """Read-only view of a payment transaction record linked to an installment."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    chit_membership_id: uuid.UUID
    installment_id: uuid.UUID
    amount_paid: Decimal
    payment_method: str
    transaction_reference: str
    receipt_number: str
    status: str
    notes: Optional[str] = None
    paid_at: datetime


class InstallmentDetailResponse(BaseModel):
    """Individual installment row including applied dividends, penalties, and payment balance."""
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
    payments: List[PaymentRecordResponse] = []


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
