import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.auction import Auction, AuctionStatus
from app.models.chit_group import ChitGroup
from app.models.chit_scheme import ChitScheme
from app.models.installment import Installment, InstallmentStatus
from app.models.membership import ChitMembership, MembershipStatus
from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app.models.payout import Payout, PayoutStatus, Surety, SuretyStatus, SuretyType
from app.models.user import User, UserRole, KYCStatus
from app.schemas.payout import (
    PayoutDetailResponse,
    PayoutDisburseRequest,
    SubstitutionCreate,
    SubstitutionResponse,
    SuretyCreate,
    SuretyResponse,
    SuretyVerifyRequest,
)


class PayoutService:
    """
    Core Chit Fund prize money payout disbursement, surety collateral verification,
    arrears auto-deduction, and defaulter substitution engine.
    """

    @staticmethod
    def _to_surety_response(s: Surety) -> SuretyResponse:
        verified_by = s.verified_by_user.full_name if s.verified_by_user else None
        return SuretyResponse(
            id=s.id,
            payout_id=s.payout_id,
            surety_type=s.surety_type,
            guarantor_name=s.guarantor_name,
            guarantor_phone=s.guarantor_phone,
            document_reference=s.document_reference,
            verification_status=s.verification_status,
            verified_by_name=verified_by,
            remarks=s.remarks,
            created_at=s.created_at,
        )

    @staticmethod
    def _to_payout_detail_response(db: Session, p: Payout) -> PayoutDetailResponse:
        # Calculate unpaid ticket arrears
        unpaid = (
            db.query(Installment)
            .filter(
                Installment.chit_membership_id == p.chit_membership_id,
                Installment.status != InstallmentStatus.PAID,
            )
            .all()
        )
        unpaid_count = len(unpaid)
        unpaid_amount = sum(max(Decimal("0.00"), i.net_due_amount - i.paid_amount) for i in unpaid)

        surety_responses = [PayoutService._to_surety_response(s) for s in p.sureties]

        return PayoutDetailResponse(
            id=p.id,
            auction_id=p.auction_id,
            chit_membership_id=p.chit_membership_id,
            ticket_number=p.membership.ticket_number,
            subscriber_name=p.membership.user.full_name,
            subscriber_phone=p.membership.user.phone,
            group_code=p.auction.chit_group.group_code,
            round_number=p.auction.month_number,
            gross_prize_amount=p.gross_prize_amount,
            foreman_charges_deducted=p.foreman_charges_deducted,
            arrears_deducted=p.arrears_deducted,
            net_disbursed_amount=p.net_disbursed_amount,
            disbursement_status=p.disbursement_status,
            disbursement_reference=p.disbursement_reference,
            disbursed_at=p.disbursed_at,
            created_at=p.created_at,
            sureties=surety_responses,
            unpaid_installments_count=unpaid_count,
            unpaid_installments_amount=unpaid_amount,
        )

    @staticmethod
    def get_or_create_auction_payout(
        db: Session,
        auction_id: uuid.UUID,
        current_user: User,
    ) -> PayoutDetailResponse:
        """Fetch or initialize the Prize Money Payout claim for a concluded auction."""
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Auction not found.",
            )

        group = auction.chit_group
        from app.services.authz_service import AuthorizationService
        AuthorizationService.check_group_access(current_user, group, db, write=False)

        if current_user.role.canonical == UserRole.MEMBER:
            if auction.winning_membership and auction.winning_membership.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Cannot view other members' payouts.",
                )

        if auction.status not in [AuctionStatus.CLOSED, AuctionStatus.FINALIZED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot initialize payout for auction in {auction.status.value} status. Auction must be CLOSED.",
            )

        if not auction.winning_membership_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This round has no winning subscriber ticket (e.g. foreman reserved or cancelled).",
            )

        payout = db.query(Payout).filter(Payout.auction_id == auction.id).first()
        if not payout:
            scheme = group.scheme
            gross_prize = (scheme.total_value - auction.winning_bid_discount).quantize(Decimal("0.01"))
            payout = Payout(
                auction_id=auction.id,
                chit_membership_id=auction.winning_membership_id,
                gross_prize_amount=gross_prize,
                foreman_charges_deducted=Decimal("0.00"),
                arrears_deducted=Decimal("0.00"),
                net_disbursed_amount=gross_prize,
                disbursement_status=PayoutStatus.PENDING_SURETY,
            )
            db.add(payout)
            db.commit()
            db.refresh(payout)

        return PayoutService._to_payout_detail_response(db, payout)

    @staticmethod
    def list_payouts(
        db: Session,
        current_user: User,
        status_filter: Optional[PayoutStatus] = None,
    ) -> List[PayoutDetailResponse]:
        """List all prize payout claims across the organization."""
        query = (
            db.query(Payout)
            .join(Auction, Payout.auction_id == Auction.id)
            .join(ChitGroup, Auction.chit_group_id == ChitGroup.id)
        )

        if current_user.role != UserRole.SUPER_ADMIN:
            query = query.filter(ChitGroup.organization_id == current_user.organization_id)

        canonical_role = current_user.role.canonical
        if canonical_role == UserRole.MEMBER:
            query = query.join(ChitMembership, Payout.chit_membership_id == ChitMembership.id).filter(
                ChitMembership.user_id == current_user.id
            )
        elif canonical_role == UserRole.MANAGER:
            query = query.filter(ChitGroup.manager_id == current_user.id)

        if status_filter:
            query = query.filter(Payout.disbursement_status == status_filter)

        payouts = query.order_by(Payout.created_at.desc()).limit(100).all()
        return [PayoutService._to_payout_detail_response(db, p) for p in payouts]

    @staticmethod
    def add_surety(
        db: Session,
        payout_id: uuid.UUID,
        payload: SuretyCreate,
        current_user: User,
    ) -> SuretyResponse:
        """Add a collateral or guarantor surety record to a payout claim."""
        payout = db.query(Payout).filter(Payout.id == payout_id).first()
        if not payout:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payout record not found.",
            )

        group = payout.auction.chit_group
        if current_user.role != UserRole.SUPER_ADMIN and group.organization_id != current_user.organization_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

        if current_user.role == UserRole.SUBSCRIBER and payout.membership.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Subscribers can only submit sureties for their own prize payouts.",
            )

        if payout.disbursement_status == PayoutStatus.DISBURSED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payout has already been disbursed. Additional sureties cannot be added.",
            )

        surety = Surety(
            payout_id=payout.id,
            surety_type=payload.surety_type,
            guarantor_name=payload.guarantor_name,
            guarantor_phone=payload.guarantor_phone,
            document_reference=payload.document_reference,
            verification_status=SuretyStatus.PENDING,
            remarks=payload.remarks,
        )
        db.add(surety)
        db.commit()
        db.refresh(surety)

        return PayoutService._to_surety_response(surety)

    @staticmethod
    def verify_surety(
        db: Session,
        surety_id: uuid.UUID,
        payload: SuretyVerifyRequest,
        current_user: User,
    ) -> SuretyResponse:
        canonical_role = current_user.role.canonical
        if canonical_role not in [UserRole.ADMIN, UserRole.MANAGER]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only authorized staff or admins may verify surety collateral.",
            )

        surety = db.query(Surety).filter(Surety.id == surety_id).first()
        if not surety:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surety record not found.",
            )

        payout = surety.payout
        group = payout.auction.chit_group
        if current_user.role != UserRole.SUPER_ADMIN and group.organization_id != current_user.organization_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

        surety.verification_status = payload.verification_status
        surety.verified_by_user_id = current_user.id
        if payload.remarks:
            surety.remarks = payload.remarks

        # Check if all sureties for payout are approved
        all_sureties = db.query(Surety).filter(Surety.payout_id == payout.id).all()
        has_verified = any(s.verification_status == SuretyStatus.VERIFIED for s in all_sureties)
        has_pending = any(s.verification_status == SuretyStatus.PENDING for s in all_sureties)

        if has_verified and not has_pending and payout.disbursement_status != PayoutStatus.DISBURSED:
            payout.disbursement_status = PayoutStatus.SURETY_APPROVED
        elif payout.disbursement_status == PayoutStatus.SURETY_APPROVED and not has_verified:
            payout.disbursement_status = PayoutStatus.PENDING_SURETY

        db.commit()
        db.refresh(surety)
        return PayoutService._to_surety_response(surety)

    @staticmethod
    def disburse_payout(
        db: Session,
        payout_id: uuid.UUID,
        payload: PayoutDisburseRequest,
        current_user: User,
    ) -> PayoutDetailResponse:
        """
        Authorizes and disburses prize funds to the prized subscriber.
        Deducts any outstanding ticket arrears and automatically clears unpaid installments in the ledger.
        """
        from app.services.authz_service import AuthorizationService
        AuthorizationService.check_payout_disbursement_permission(current_user)

        payout = db.query(Payout).filter(Payout.id == payout_id).with_for_update().first()
        if not payout:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payout record not found.",
            )

        group = payout.auction.chit_group
        if current_user.role != UserRole.SUPER_ADMIN and group.organization_id != current_user.organization_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

        if payout.disbursement_status == PayoutStatus.DISBURSED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prize money has already been disbursed.",
            )

        if payout.disbursement_status != PayoutStatus.SURETY_APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot disburse: Surety collateral is not approved (Current status: {payout.disbursement_status.value}).",
            )

        # Calculate outstanding arrears on this ticket
        unpaid_installments = (
            db.query(Installment)
            .filter(
                Installment.chit_membership_id == payout.chit_membership_id,
                Installment.status != InstallmentStatus.PAID,
            )
            .order_by(Installment.month_number.asc())
            .all()
        )

        total_arrears = sum(max(Decimal("0.00"), i.net_due_amount - i.paid_amount) for i in unpaid_installments)
        arrears_to_deduct = total_arrears if payload.auto_clear_arrears else Decimal("0.00")

        net_disbursed = (
            payout.gross_prize_amount - arrears_to_deduct - payload.foreman_charges_deducted
        ).quantize(Decimal("0.01"))

        if net_disbursed < Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Negative net disbursement (₹{net_disbursed:,.2f}). Arrears and documentation charges exceed gross prize.",
            )

        # Auto-clear deducted arrears in the installment ledger
        if payload.auto_clear_arrears and unpaid_installments:
            now_utc = datetime.now(timezone.utc)
            ym = now_utc.strftime("%Y%m")

            for inst in unpaid_installments:
                remaining_due = (inst.net_due_amount - inst.paid_amount).quantize(Decimal("0.01"))
                if remaining_due > Decimal("0.00"):
                    inst.paid_amount = inst.net_due_amount
                    inst.status = InstallmentStatus.PAID

                    # Record settlement ledger entry
                    payment = Payment(
                        organization_id=group.organization_id,
                        chit_membership_id=payout.chit_membership_id,
                        installment_id=inst.id,
                        amount_paid=remaining_due,
                        payment_method=PaymentMethod.BANK_TRANSFER,
                        transaction_reference=f"PAYOUT-DEDUCT-{uuid.uuid4().hex[:8]}",
                        receipt_number=f"REC-{ym}-{uuid.uuid4().hex[:6].upper()}",
                        status=PaymentStatus.COMPLETED,
                        recorded_by_user_id=current_user.id,
                        notes=f"Auto-deducted from prize money disbursement (Ref: {payload.disbursement_reference})",
                        paid_at=now_utc,
                    )
                    db.add(payment)

        payout.foreman_charges_deducted = payload.foreman_charges_deducted
        payout.arrears_deducted = arrears_to_deduct
        payout.net_disbursed_amount = net_disbursed
        payout.disbursement_status = PayoutStatus.DISBURSED
        payout.disbursement_reference = payload.disbursement_reference
        payout.disbursed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(payout)

        return PayoutService._to_payout_detail_response(db, payout)

    @staticmethod
    def substitute_defaulter(
        db: Session,
        payload: SubstitutionCreate,
        current_user: User,
    ) -> SubstitutionResponse:
        """
        Substitutes a defaulted non-prized subscriber with a new KYC-verified member.
        Calculates statutory refund payable upon group termination per Section 28 of Chit Funds Act.
        """
        if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN, UserRole.BRANCH_MANAGER]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only authorized staff or admins may execute member substitutions.",
            )

        old_membership = (
            db.query(ChitMembership)
            .filter(ChitMembership.id == payload.chit_membership_id)
            .first()
        )
        if not old_membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscribed ticket not found.",
            )

        group = old_membership.chit_group
        if current_user.role != UserRole.SUPER_ADMIN and group.organization_id != current_user.organization_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

        if old_membership.status == MembershipStatus.PRIZED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prized subscribers cannot be substituted. Legal recovery must be initiated against sureties.",
            )

        new_user = db.query(User).filter(User.id == payload.new_user_id).first()
        if not new_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Replacement member not found.")

        if new_user.kyc_status != KYCStatus.VERIFIED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Replacement member KYC is not verified ({new_user.kyc_status.value}).",
            )

        # Check if new user is already enrolled in this group
        existing_sub = (
            db.query(ChitMembership)
            .filter(
                ChitMembership.chit_group_id == group.id,
                ChitMembership.user_id == new_user.id,
            )
            .first()
        )
        if existing_sub:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Replacement subscriber already holds an allocated ticket in this circle.",
            )

        # Statutory Refund Calculation:
        # Total Paid by Old Member - Foreman Commission - Accrued Penalties
        total_paid = sum(i.paid_amount for i in old_membership.installments)
        scheme = group.scheme
        foreman_commission = (scheme.total_value * (scheme.foreman_commission_pct / Decimal(100))).quantize(Decimal("0.01"))
        total_penalties = sum(i.penalty_amount for i in old_membership.installments)

        refund_payable = max(Decimal("0.00"), total_paid - foreman_commission - total_penalties)

        # Execute substitution: transfer ticket to new user and re-activate
        old_user_id = old_membership.user_id
        old_membership.user_id = new_user.id
        old_membership.status = MembershipStatus.ACTIVE

        db.commit()
        db.refresh(old_membership)

        return SubstitutionResponse(
            old_membership_id=old_membership.id,
            new_membership_id=old_membership.id,
            ticket_number=old_membership.ticket_number,
            group_code=group.group_code,
            total_paid_by_old_member=total_paid,
            foreman_commission_deduction=foreman_commission,
            statutory_refund_amount=refund_payable,
            refund_payable_date=group.end_date,
            status="SUBSTITUTED_AND_TRANSFERRED",
        )
