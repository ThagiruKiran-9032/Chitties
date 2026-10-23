import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_permission
from app.models.chit_group import ChitGroup
from app.models.installment import Installment
from app.models.membership import ChitMembership
from app.models.payment import Payment
from app.models.user import User, UserRole
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.services.authz_service import Permission
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments & Idempotent Collection"])


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def record_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RECORD_PAYMENTS)),
):
    """
    Record an installment payment with idempotency guarantee.
    Enforces that Managers cannot record payments, Members can only pay own tickets,
    and Accountants/Admins can record payments.
    """
    return PaymentService.process_payment(db, payload, current_user)


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment_receipt(
    payment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch digital receipt metadata for a specific payment transaction.
    Enforces role-based data isolation:
    - Member: can only view own payment receipts.
    - Manager: can only view receipts for assigned groups.
    - Admin & Accountant: can view all organization receipts.
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment receipt not found.")

    if current_user.role != UserRole.SUPER_ADMIN and payment.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment receipt not found.")

    canonical_role = current_user.role.canonical
    if canonical_role == UserRole.MEMBER and payment.membership.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment receipt not found.")

    if canonical_role == UserRole.MANAGER and payment.installment.chit_group.manager_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment receipt not found.")

    return PaymentService._to_payment_response(payment)


@router.get("", response_model=List[PaymentResponse])
def list_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List payments with role-based scoping:
    - Admin & Accountant: all payments in organization.
    - Manager: payments for assigned groups only.
    - Member: payments for own tickets only.
    """
    query = db.query(Payment)
    if current_user.role != UserRole.SUPER_ADMIN:
        query = query.filter(Payment.organization_id == current_user.organization_id)

    canonical_role = current_user.role.canonical

    if canonical_role == UserRole.MEMBER:
        query = query.join(ChitMembership, Payment.chit_membership_id == ChitMembership.id).filter(
            ChitMembership.user_id == current_user.id
        )
    elif canonical_role == UserRole.MANAGER:
        query = (
            query.join(Installment, Payment.installment_id == Installment.id)
            .join(ChitGroup, Installment.chit_group_id == ChitGroup.id)
            .filter(ChitGroup.manager_id == current_user.id)
        )

    payments = query.order_by(Payment.paid_at.desc()).limit(100).all()
    return [PaymentService._to_payment_response(p) for p in payments]
