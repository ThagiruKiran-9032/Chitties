import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_roles, require_permission
from app.services.authz_service import Permission
from app.models.payout import PayoutStatus
from app.models.user import User, UserRole
from app.schemas.payout import (
    PayoutDetailResponse,
    PayoutDisburseRequest,
    SubstitutionCreate,
    SubstitutionResponse,
    SuretyCreate,
    SuretyResponse,
    SuretyVerifyRequest,
)
from app.services.payout_service import PayoutService

router = APIRouter(prefix="/payouts", tags=["Prize Money Payouts & Sureties"])


@router.get("", response_model=List[PayoutDetailResponse])
def list_payouts(
    status: Optional[PayoutStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all prize payout claims across the organization."""
    return PayoutService.list_payouts(db, current_user, status)


@router.get("/auction/{auction_id}", response_model=PayoutDetailResponse)
def get_or_create_auction_payout(
    auction_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch or initialize the Prize Money Payout claim for a concluded auction."""
    return PayoutService.get_or_create_auction_payout(db, auction_id, current_user)


@router.post("/{payout_id}/sureties", response_model=SuretyResponse, status_code=status.HTTP_201_CREATED)
def add_surety(
    payout_id: uuid.UUID,
    payload: SuretyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a guarantor, salary certificate, or property collateral surety."""
    return PayoutService.add_surety(db, payout_id, payload, current_user)


@router.patch("/sureties/{surety_id}/verify", response_model=SuretyResponse)
def verify_surety(
    surety_id: uuid.UUID,
    payload: SuretyVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission(Permission.PROCESS_PAYOUTS)
    ),
):
    """Verify or reject a submitted surety security record."""
    return PayoutService.verify_surety(db, surety_id, payload, current_user)


@router.post("/{payout_id}/disburse", response_model=PayoutDetailResponse)
def disburse_payout(
    payout_id: uuid.UUID,
    payload: PayoutDisburseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission(Permission.APPROVE_SENSITIVE_FINANCIAL_OPS)
    ),
):
    """
    Authorize and disburse prize money to the prized subscriber.
    Auto-deducts and clears any outstanding installment arrears in the ledger.
    """
    return PayoutService.disburse_payout(db, payout_id, payload, current_user)


@router.post("/substitute", response_model=SubstitutionResponse)
def substitute_defaulter(
    payload: SubstitutionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission(Permission.MANAGE_USERS)
    ),
):
    """Substitute a non-prized defaulting subscriber with a new KYC-verified member."""
    return PayoutService.substitute_defaulter(db, payload, current_user)
