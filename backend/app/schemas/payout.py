import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.payout import PayoutStatus, SuretyStatus, SuretyType


class SuretyCreate(BaseModel):
    """Payload to lodge collateral, salary certificate, or guarantor security."""
    surety_type: SuretyType
    guarantor_name: Optional[str] = Field(None, max_length=150, description="Full legal name of co-signer.")
    guarantor_phone: Optional[str] = Field(None, max_length=20, description="Phone number of guarantor.")
    document_reference: str = Field(..., max_length=255, description="Document reference number or deed ID.")
    remarks: Optional[str] = Field(None, max_length=500, description="Collateral details or valuation.")


class SuretyResponse(BaseModel):
    """Guarantor or collateral security record."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    payout_id: uuid.UUID
    surety_type: SuretyType
    guarantor_name: Optional[str] = None
    guarantor_phone: Optional[str] = None
    document_reference: str
    verification_status: SuretyStatus
    verified_by_name: Optional[str] = None
    remarks: Optional[str] = None
    created_at: datetime


class SuretyVerifyRequest(BaseModel):
    """Payload for manager/admin to verify or reject a submitted surety."""
    verification_status: SuretyStatus = Field(..., description="VERIFIED or REJECTED")
    remarks: Optional[str] = Field(None, max_length=500, description="Verification notes or reason.")


class PayoutDetailResponse(BaseModel):
    """Detailed payout claim record including arrears calculations and sureties."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    auction_id: uuid.UUID
    chit_membership_id: uuid.UUID
    ticket_number: int
    subscriber_name: str
    subscriber_phone: str
    group_code: str
    round_number: int
    gross_prize_amount: Decimal
    foreman_charges_deducted: Decimal
    arrears_deducted: Decimal
    net_disbursed_amount: Decimal
    disbursement_status: PayoutStatus
    disbursement_reference: Optional[str] = None
    disbursed_at: Optional[datetime] = None
    created_at: datetime
    sureties: List[SuretyResponse] = []
    unpaid_installments_count: int = 0
    unpaid_installments_amount: Decimal = Decimal("0.00")


class PayoutDisburseRequest(BaseModel):
    """Payload to authorize and release prize money disbursement."""
    disbursement_reference: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Bank UTR, NEFT reference, or Cheque number.",
    )
    foreman_charges_deducted: Decimal = Field(
        Decimal("0.00"),
        ge=0,
        description="Documentation or processing fee to deduct.",
    )
    auto_clear_arrears: bool = Field(
        True,
        description="Whether to automatically clear any outstanding ticket arrears from the prize money.",
    )
    notes: Optional[str] = Field(None, max_length=500)


class SubstitutionCreate(BaseModel):
    """Payload to substitute a defaulted non-prized subscriber with a new verified member."""
    chit_membership_id: uuid.UUID = Field(..., description="ID of the defaulted membership.")
    new_user_id: uuid.UUID = Field(..., description="ID of the KYC-verified replacement member.")
    reason: Optional[str] = Field(None, max_length=500, description="Audit reason for substitution.")


class SubstitutionResponse(BaseModel):
    """Settlement statement for a substituted subscriber per statutory regulations."""
    old_membership_id: uuid.UUID
    new_membership_id: uuid.UUID
    ticket_number: int
    group_code: str
    total_paid_by_old_member: Decimal
    foreman_commission_deduction: Decimal
    statutory_refund_amount: Decimal
    refund_payable_date: date
    status: str
