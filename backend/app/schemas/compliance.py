import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict

from app.models.compliance import DepositType, LienStatus, FilingType, FilingStatus


# ============================================================================
# SECTION 20 SECURITY DEPOSITS
# ============================================================================

class SecurityDepositCreate(BaseModel):
    group_id: uuid.UUID
    deposit_type: DepositType = DepositType.FIXED_DEPOSIT
    bank_name: str = Field(..., min_length=2, max_length=150)
    account_or_fdr_number: str = Field(..., min_length=2, max_length=100)
    amount: Decimal = Field(..., gt=0)
    deposit_date: date
    maturity_date: date
    registrar_order_reference: str = Field(..., min_length=2, max_length=100)
    remarks: Optional[str] = None


class SecurityDepositVerifyRequest(BaseModel):
    lien_status: LienStatus
    remarks: Optional[str] = None


class SecurityDepositResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    group_id: uuid.UUID
    group_code: Optional[str] = None
    group_name: Optional[str] = None
    chit_value: Optional[Decimal] = None
    deposit_type: DepositType
    bank_name: str
    account_or_fdr_number: str
    amount: Decimal
    deposit_date: date
    maturity_date: date
    registrar_order_reference: str
    lien_status: LienStatus
    remarks: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# ============================================================================
# REGISTRAR FILINGS & STATUTORY FORMS
# ============================================================================

class RegistrarFilingCreate(BaseModel):
    group_id: uuid.UUID
    auction_id: Optional[uuid.UUID] = None
    form_type: FilingType
    filing_reference_number: str = Field(..., min_length=2, max_length=100)
    filed_date: date
    registrar_office_name: str = Field(..., min_length=2, max_length=150)
    acknowledgment_number: Optional[str] = None
    notes: Optional[str] = None


class RegistrarFilingUpdate(BaseModel):
    acknowledgment_number: Optional[str] = None
    status: Optional[FilingStatus] = None
    notes: Optional[str] = None


class RegistrarFilingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    group_id: uuid.UUID
    group_code: Optional[str] = None
    auction_id: Optional[uuid.UUID] = None
    form_type: FilingType
    filing_reference_number: str
    filed_date: date
    registrar_office_name: str
    acknowledgment_number: Optional[str] = None
    status: FilingStatus
    metadata_payload: Optional[Any] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class FormXIVMinutesPayload(BaseModel):
    chit_group_code: str
    chit_group_name: str
    prior_sanction_number: str
    auction_id: uuid.UUID
    auction_round: int
    auction_date: datetime
    chit_value: Decimal
    winning_bid_discount: Decimal
    foreman_commission: Decimal
    dividend_total: Decimal
    dividend_per_ticket: Decimal
    prized_amount: Decimal
    prized_ticket_number: int
    prized_subscriber_name: str
    prized_subscriber_phone: Optional[str] = None
    prized_subscriber_address: Optional[str] = None
    registrar_office: str
    filing_deadline: date
    bids_recorded: List[dict] = []
    foreman_name: str = "Authorized Foreman Representative"


# ============================================================================
# AUDIT & FINANCIAL BALANCE SHEET
# ============================================================================

class CircleBalanceSheetResponse(BaseModel):
    group_id: uuid.UUID
    group_code: str
    group_name: str
    total_chit_value: Decimal
    total_installments_demanded: Decimal
    total_installments_collected: Decimal
    total_late_penalties_collected: Decimal
    total_doc_fees_collected: Decimal
    total_gross_inflow: Decimal
    total_prize_money_disbursed: Decimal
    total_defaulter_refunds_paid: Decimal
    total_gross_outflow: Decimal
    total_dividends_distributed: Decimal
    foreman_commission_accrued: Decimal
    current_arrears_receivable: Decimal
    sec_20_lien_pledged: Decimal
    net_cash_pool_balance: Decimal
    rounds_completed: int
    total_rounds: int
    is_balanced: bool


class DelinquentTicketSummary(BaseModel):
    ticket_id: uuid.UUID
    ticket_number: int
    subscriber_name: str
    subscriber_phone: Optional[str] = None
    overdue_amount: Decimal
    unpaid_installments_count: int
    oldest_due_date: date
    days_overdue: int
    aging_bucket: str  # "0-30", "31-60", "61-90", "90+"


class DelinquencyAgingResponse(BaseModel):
    group_id: uuid.UUID
    group_code: str
    current_dues: Decimal  # 0-30 days
    dues_31_to_60: Decimal
    dues_61_to_90: Decimal
    npa_over_90: Decimal
    total_delinquent_amount: Decimal
    total_defaulters_count: int
    delinquent_tickets: List[DelinquentTicketSummary] = []


class ComplianceSystemSummary(BaseModel):
    total_lien_pledged: Decimal
    active_circles_covered: int
    total_filings_count: int
    pending_filings_count: int
    total_prize_disbursed: Decimal
    total_arrears_uncollected: Decimal
