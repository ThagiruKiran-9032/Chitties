import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.compliance import DepositType, LienStatus, FilingType, FilingStatus
from app.models.user import User, UserRole
from app.schemas.compliance import (
    SecurityDepositCreate,
    SecurityDepositVerifyRequest,
    SecurityDepositResponse,
    RegistrarFilingCreate,
    RegistrarFilingUpdate,
    RegistrarFilingResponse,
    FormXIVMinutesPayload,
    CircleBalanceSheetResponse,
    DelinquencyAgingResponse,
    ComplianceSystemSummary,
)
from app.services.compliance_service import ComplianceService

router = APIRouter(prefix="/compliance", tags=["Regulatory Compliance, Registrar Filings & Audit"])


# ============================================================================
# SECTION 20 SECURITY DEPOSITS
# ============================================================================

@router.get("/deposits", response_model=List[SecurityDepositResponse])
def list_security_deposits(
    group_id: Optional[uuid.UUID] = None,
    lien_status: Optional[LienStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all Section 20 statutory security deposits lodged with the State Registrar."""
    return ComplianceService.list_security_deposits(
        db, current_user.organization_id, group_id, lien_status
    )


@router.post(
    "/deposits",
    response_model=SecurityDepositResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN, UserRole.BRANCH_MANAGER]))],
)
def lodge_security_deposit(
    payload: SecurityDepositCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lodge a Section 20 Foreman Security Deposit (FDR / Bank Guarantee)
    mandating 100% of the aggregate chit value before commencing the circle.
    """
    dep = ComplianceService.lodge_security_deposit(
        db, current_user.organization_id, payload, current_user.id
    )
    # Re-fetch formatted response
    items = ComplianceService.list_security_deposits(db, current_user.organization_id, group_id=dep.group_id)
    match = next((x for x in items if x["id"] == dep.id), None)
    return match or dep


@router.patch(
    "/deposits/{deposit_id}/verify",
    response_model=SecurityDepositResponse,
    dependencies=[Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN]))],
)
def verify_security_deposit_lien(
    deposit_id: uuid.UUID,
    payload: SecurityDepositVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Verify or update lien pledge status (PLEDGED / RELEASED) with Registrar order reference.
    """
    dep = ComplianceService.verify_security_deposit(
        db, current_user.organization_id, deposit_id, payload, current_user.id
    )
    items = ComplianceService.list_security_deposits(db, current_user.organization_id, group_id=dep.group_id)
    match = next((x for x in items if x["id"] == dep.id), None)
    return match or dep


# ============================================================================
# STATUTORY REGISTRAR FILINGS & FORM XIV
# ============================================================================

@router.get("/filings", response_model=List[RegistrarFilingResponse])
def list_registrar_filings(
    group_id: Optional[uuid.UUID] = None,
    form_type: Optional[FilingType] = None,
    filing_status: Optional[FilingStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List statutory filings submitted to the State Registrar of Chits."""
    return ComplianceService.list_registrar_filings(
        db, current_user.organization_id, group_id, form_type, filing_status
    )


@router.post(
    "/filings",
    response_model=RegistrarFilingResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN, UserRole.BRANCH_MANAGER]))],
)
def record_registrar_filing(
    payload: RegistrarFilingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record a statutory filing lodged with the Registrar (Form I, II, XIV, XXI)."""
    filing = ComplianceService.create_registrar_filing(
        db, current_user.organization_id, payload, current_user.id
    )
    items = ComplianceService.list_registrar_filings(db, current_user.organization_id, group_id=filing.group_id)
    match = next((x for x in items if x["id"] == filing.id), None)
    return match or filing


@router.patch(
    "/filings/{filing_id}",
    response_model=RegistrarFilingResponse,
    dependencies=[Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN, UserRole.BRANCH_MANAGER]))],
)
def update_registrar_filing(
    filing_id: uuid.UUID,
    payload: RegistrarFilingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update acknowledgment number and status of a statutory filing."""
    filing = ComplianceService.update_registrar_filing(
        db, current_user.organization_id, filing_id, payload, current_user.id
    )
    items = ComplianceService.list_registrar_filings(db, current_user.organization_id, group_id=filing.group_id)
    match = next((x for x in items if x["id"] == filing.id), None)
    return match or filing


@router.get("/auctions/{auction_id}/form-xiv", response_model=FormXIVMinutesPayload)
def get_form_xiv_minutes(
    auction_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate statutory Form XIV (Minutes of Auction Proceedings)
    for a concluded auction round ready for Registrar submission.
    """
    return ComplianceService.generate_form_xiv_minutes_dict(
        db, current_user.organization_id, auction_id
    )


# ============================================================================
# AUDIT & FINANCIAL BALANCE SHEET
# ============================================================================

@router.get("/groups/{group_id}/balance-sheet", response_model=CircleBalanceSheetResponse)
def get_circle_balance_sheet(
    group_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate double-entry financial balance sheet for a chit circle,
    reconciling collections, disbursements, dividends, and commission.
    """
    return ComplianceService.get_circle_balance_sheet(
        db, current_user.organization_id, group_id
    )


@router.get("/groups/{group_id}/delinquency-report", response_model=DelinquencyAgingResponse)
def get_delinquency_report(
    group_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate subscriber delinquency aging report (30/60/90 days overdue).
    """
    return ComplianceService.get_delinquency_aging(
        db, current_user.organization_id, group_id
    )


@router.get("/system-summary", response_model=ComplianceSystemSummary)
def get_compliance_system_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get organization-wide regulatory summary:
    Total Section 20 lien pledged, active circles covered, and filing statuses.
    """
    return ComplianceService.get_compliance_system_summary(
        db, current_user.organization_id
    )
