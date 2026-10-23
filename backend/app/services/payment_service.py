import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.chit_group import ChitGroup
from app.models.installment import Installment, InstallmentStatus
from app.models.membership import ChitMembership
from app.models.payment import Payment, PaymentStatus
from app.models.user import User, UserRole
from app.schemas.payment import (
    InstallmentDetailResponse,
    MemberLedgerSummaryResponse,
    PaymentCreate,
    PaymentResponse,
)


class PaymentService:
    """
    Core Chit Fund payment processing, idempotency enforcement, ledger balancing,
    digital receipt generation, and penalty application service.
    """

    @staticmethod
    def _to_payment_response(p: Payment) -> PaymentResponse:
        return PaymentResponse(
            id=p.id,
            organization_id=p.organization_id,
            chit_membership_id=p.chit_membership_id,
            installment_id=p.installment_id,
            ticket_number=p.membership.ticket_number if p.membership else None,
            subscriber_name=p.membership.user.full_name if (p.membership and p.membership.user) else None,
            group_code=p.installment.chit_group.group_code if (p.installment and p.installment.chit_group) else None,
            month_number=p.installment.month_number if p.installment else None,
            amount_paid=p.amount_paid,
            payment_method=p.payment_method,
            transaction_reference=p.transaction_reference,
            receipt_number=p.receipt_number,
            status=p.status,
            recorded_by_name=p.recorded_by_user.full_name if p.recorded_by_user else None,
            notes=p.notes,
            paid_at=p.paid_at,
        )

    @staticmethod
    def _to_installment_response(i: Installment) -> InstallmentDetailResponse:
        remaining = max(Decimal("0.00"), i.net_due_amount - i.paid_amount)
        sub_name = i.membership.user.full_name if (i.membership and i.membership.user) else "Unknown"
        ticket_no = i.membership.ticket_number if i.membership else 0

        payment_responses = [PaymentService._to_payment_response(p) for p in i.payments]

        return InstallmentDetailResponse(
            id=i.id,
            chit_group_id=i.chit_group_id,
            chit_membership_id=i.chit_membership_id,
            ticket_number=ticket_no,
            subscriber_name=sub_name,
            month_number=i.month_number,
            due_date=i.due_date,
            gross_amount=i.gross_amount,
            dividend_amount=i.dividend_amount,
            penalty_amount=i.penalty_amount,
            net_due_amount=i.net_due_amount,
            paid_amount=i.paid_amount,
            remaining_balance=remaining,
            status=i.status,
            payments=payment_responses,
        )

    @staticmethod
    def process_payment(
        db: Session,
        payload: PaymentCreate,
        current_user: User,
    ) -> PaymentResponse:
        """
        Idempotent payment collection against an installment obligation.
        Locks the installment row, records settlement, adjusts paid amount,
        and transitions status to PARTIALLY_PAID or PAID.
        """
        # Idempotency check: if transaction_reference already exists, return existing record
        existing = db.query(Payment).filter(Payment.transaction_reference == payload.transaction_reference).first()
        if existing:
            if current_user.role != UserRole.SUPER_ADMIN and existing.organization_id != current_user.organization_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied.",
                )
            return PaymentService._to_payment_response(existing)

        # Lock installment row for update to prevent concurrent double-collection
        installment = (
            db.query(Installment)
            .filter(Installment.id == payload.installment_id)
            .with_for_update()
            .first()
        )
        if not installment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Installment obligation not found.",
            )

        group = db.query(ChitGroup).filter(ChitGroup.id == installment.chit_group_id).first()
        if current_user.role != UserRole.SUPER_ADMIN and group.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cross-tenant installment collection blocked.",
            )

        membership = installment.membership
        from app.services.authz_service import AuthorizationService
        AuthorizationService.check_payment_record_permission(current_user, membership.user_id)

        balance_remaining = (installment.net_due_amount - installment.paid_amount).quantize(Decimal("0.01"))
        if balance_remaining <= Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This installment is already fully settled.",
            )

        if payload.amount > balance_remaining:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment amount ₹{payload.amount:,.2f} exceeds outstanding installment balance of ₹{balance_remaining:,.2f}.",
            )

        now = datetime.now(timezone.utc)
        ym = now.strftime("%Y%m")
        seq = uuid.uuid4().hex[:6].upper()
        receipt_number = f"REC-{ym}-{seq}"

        payment = Payment(
            organization_id=group.organization_id,
            chit_membership_id=membership.id,
            installment_id=installment.id,
            amount_paid=payload.amount,
            payment_method=payload.payment_method,
            transaction_reference=payload.transaction_reference,
            receipt_number=receipt_number,
            status=PaymentStatus.COMPLETED,
            recorded_by_user_id=current_user.id,
            notes=payload.notes,
            paid_at=now,
        )
        db.add(payment)

        # Update installment paid progress
        new_paid = (installment.paid_amount + payload.amount).quantize(Decimal("0.01"))
        installment.paid_amount = new_paid

        if new_paid >= installment.net_due_amount:
            installment.status = InstallmentStatus.PAID
        else:
            installment.status = InstallmentStatus.PARTIALLY_PAID

        db.commit()
        db.refresh(payment)
        db.refresh(installment)

        return PaymentService._to_payment_response(payment)

    @staticmethod
    def get_payment_receipt(
        db: Session,
        payment_id: uuid.UUID,
        current_user: User,
    ) -> PaymentResponse:
        """Fetch a digital payment receipt."""
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment record not found.",
            )

        if current_user.role != UserRole.SUPER_ADMIN and payment.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied.",
            )

        return PaymentService._to_payment_response(payment)

    @staticmethod
    def get_group_installments(
        db: Session,
        group_id: uuid.UUID,
        current_user: User,
        status_filter: Optional[InstallmentStatus] = None,
        month_number: Optional[int] = None,
    ) -> List[InstallmentDetailResponse]:
        """List installment ledger rows for a chit fund group."""
        group = db.query(ChitGroup).filter(ChitGroup.id == group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chit Group not found.",
            )

        if current_user.role != UserRole.SUPER_ADMIN and group.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied.",
            )

        query = db.query(Installment).filter(Installment.chit_group_id == group_id)
        if status_filter:
            query = query.filter(Installment.status == status_filter)
        if month_number:
            query = query.filter(Installment.month_number == month_number)

        installments = query.order_by(Installment.month_number.asc(), Installment.due_date.asc()).all()
        return [PaymentService._to_installment_response(i) for i in installments]

    @staticmethod
    def get_member_ledger(
        db: Session,
        membership_id: uuid.UUID,
        current_user: User,
    ) -> MemberLedgerSummaryResponse:
        """Generate comprehensive ledger statement for a subscriber's ticket."""
        membership = db.query(ChitMembership).filter(ChitMembership.id == membership_id).first()
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chit membership ticket not found.",
            )

        group = membership.chit_group
        if current_user.role != UserRole.SUPER_ADMIN and group.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied.",
            )

        if current_user.role == UserRole.SUBSCRIBER and membership.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Subscribers can only access their own statement.",
            )

        installments = (
            db.query(Installment)
            .filter(Installment.chit_membership_id == membership_id)
            .order_by(Installment.month_number.asc())
            .all()
        )

        total_gross = Decimal("0.00")
        total_dividends = Decimal("0.00")
        total_penalties = Decimal("0.00")
        total_net_due = Decimal("0.00")
        total_paid = Decimal("0.00")

        installment_responses = []
        for i in installments:
            total_gross += i.gross_amount
            total_dividends += i.dividend_amount
            total_penalties += i.penalty_amount
            total_net_due += i.net_due_amount
            total_paid += i.paid_amount
            installment_responses.append(PaymentService._to_installment_response(i))

        total_balance = max(Decimal("0.00"), total_net_due - total_paid)

        return MemberLedgerSummaryResponse(
            chit_membership_id=membership.id,
            chit_group_id=group.id,
            group_code=group.group_code,
            ticket_number=membership.ticket_number,
            subscriber_name=membership.user.full_name,
            subscriber_email=membership.user.email,
            subscriber_phone=membership.user.phone,
            total_gross_obligations=total_gross,
            total_dividends_earned=total_dividends,
            total_penalties_applied=total_penalties,
            total_net_due=total_net_due,
            total_amount_paid=total_paid,
            total_outstanding_balance=total_balance,
            installments=installment_responses,
        )

    @staticmethod
    def apply_penalty(
        db: Session,
        installment_id: uuid.UUID,
        penalty_amount: Decimal,
        reason: Optional[str],
        current_user: User,
    ) -> InstallmentDetailResponse:
        """Apply an overdue late fee penalty and recalculate net due amount."""
        if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN, UserRole.BRANCH_MANAGER]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only authorized staff or admins may levy late fees.",
            )

        installment = (
            db.query(Installment)
            .filter(Installment.id == installment_id)
            .with_for_update()
            .first()
        )
        if not installment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Installment not found.",
            )

        group = installment.chit_group
        if current_user.role != UserRole.SUPER_ADMIN and group.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied.",
            )

        installment.penalty_amount = (installment.penalty_amount + penalty_amount).quantize(Decimal("0.01"))
        installment.net_due_amount = (
            installment.gross_amount - installment.dividend_amount + installment.penalty_amount
        ).quantize(Decimal("0.01"))

        if installment.paid_amount >= installment.net_due_amount:
            installment.status = InstallmentStatus.PAID
        elif installment.paid_amount > Decimal("0.00"):
            installment.status = InstallmentStatus.PARTIALLY_PAID
        else:
            installment.status = InstallmentStatus.OVERDUE

        db.commit()
        db.refresh(installment)
        return PaymentService._to_installment_response(installment)
