import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_permission
from app.models.chit_group import ChitGroup
from app.models.installment import InstallmentStatus
from app.models.membership import ChitMembership
from app.models.user import User, UserRole
from app.schemas.installment import (
    InstallmentDetailResponse,
    MemberLedgerSummaryResponse,
    PenaltyCreate,
)
from app.services.authz_service import AuthorizationService, Permission
from app.services.installment_service import InstallmentService

router = APIRouter(prefix="/installments", tags=["Installment Ledger"])


@router.get("/group/{group_id}", response_model=List[InstallmentDetailResponse])
def get_group_installments(
    group_id: uuid.UUID,
    status_filter: Optional[InstallmentStatus] = Query(None, alias="status"),
    month: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve all installment obligations for a chit group.
    - Admin & Accountant: Full access within organization.
    - Manager: Access restricted to assigned groups.
    - Member: Strictly forbidden from viewing group-wide subscriber dues.
    """
    group = db.query(ChitGroup).filter(ChitGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chit Group not found.")

    canonical_role = current_user.role.canonical
    if canonical_role == UserRole.MEMBER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Members are not permitted to view group-wide subscriber ledger obligations.",
        )

    AuthorizationService.check_group_access(current_user, group, db, write=False)
    return InstallmentService.get_group_installments(db, group_id, current_user, status_filter, month)


@router.get("/membership/{membership_id}", response_model=MemberLedgerSummaryResponse)
def get_member_ledger(
    membership_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve full chronological ledger statement and payment history for a subscriber ticket.
    - Member: Can only access their own subscribed ticket statement.
    - Manager: Can only access tickets for their assigned groups.
    - Admin & Accountant: Full access within organization.
    """
    membership = db.query(ChitMembership).filter(ChitMembership.id == membership_id).first()
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chit membership ticket not found.")

    group = membership.chit_group
    if current_user.role != UserRole.SUPER_ADMIN and group.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chit membership ticket not found.")

    canonical_role = current_user.role.canonical
    if canonical_role == UserRole.MEMBER and membership.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Subscribers can only access their own statement.",
        )

    if canonical_role == UserRole.MANAGER and group.manager_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chit membership ticket not found.",
        )

    return InstallmentService.get_member_ledger(db, membership_id, current_user)


@router.post("/{installment_id}/penalty", response_model=InstallmentDetailResponse)
def apply_penalty(
    installment_id: uuid.UUID,
    payload: PenaltyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.APPROVE_SENSITIVE_FINANCIAL_OPS)),
):
    """
    Apply an overdue penalty/late fee to an installment obligation (Admin only).
    Enforces financial audit and authorization control.
    """
    return InstallmentService.apply_penalty(db, installment_id, payload.penalty_amount, payload.reason, current_user)
