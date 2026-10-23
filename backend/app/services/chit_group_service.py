import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional, List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.chit_scheme import ChitScheme
from app.models.chit_group import ChitGroup, ChitGroupStatus
from app.models.membership import ChitMembership, MembershipStatus
from app.models.user import User, UserRole, KYCStatus
from app.models.installment import Installment, InstallmentStatus
from app.models.auction import Auction, AuctionStatus


class ChitGroupService:
    """
    Business Domain Service coordinating Chit Group lifecycles,
    strict capacity rules, member ticket allocation, and schedule generation.
    """

    @classmethod
    def enroll_member(
        cls,
        db: Session,
        group_id: uuid.UUID,
        user_id: uuid.UUID,
        ticket_number: int,
        caller: User,
    ) -> ChitMembership:
        """
        Enroll a verified subscriber into a specific ticket number in a ChitGroup.
        Enforces KYC compliance, capacity limits, and strictly single ticket per user.
        """
        group = db.query(ChitGroup).filter(ChitGroup.id == group_id).first()
        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chit Group not found")

        scheme = db.query(ChitScheme).filter(ChitScheme.id == group.scheme_id).first()
        if not scheme:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated Chit Scheme not found")

        # 1. Group lifecycle check
        if group.status not in [ChitGroupStatus.DRAFT, ChitGroupStatus.ENROLLING]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot enroll members into group with status '{group.status.value}'",
            )

        # 2. Subscriber validation
        subscriber = db.query(User).filter(User.id == user_id).first()
        if not subscriber:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscriber user not found")

        if caller.role != UserRole.SUPER_ADMIN and subscriber.organization_id != caller.organization_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot enroll subscriber from another organization")

        # 3. KYC Compliance check
        if subscriber.kyc_status != KYCStatus.VERIFIED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Subscriber KYC is '{subscriber.kyc_status.value}'. Only VERIFIED subscribers can be enrolled.",
            )

        # 4. Ticket range check (1 to N)
        max_tickets = scheme.duration_months
        if ticket_number < 1 or ticket_number > max_tickets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid ticket number. Must be between 1 and {max_tickets}",
            )

        # 5. Check if user already holds a ticket in this group (Strictly 1 ticket per user)
        existing_user_membership = db.query(ChitMembership).filter(
            ChitMembership.chit_group_id == group_id,
            ChitMembership.user_id == user_id,
        ).first()
        if existing_user_membership:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Subscriber already holds Ticket #{existing_user_membership.ticket_number} in this group. Multiple tickets are prohibited.",
            )

        # 6. Check if ticket number is already assigned
        existing_ticket = db.query(ChitMembership).filter(
            ChitMembership.chit_group_id == group_id,
            ChitMembership.ticket_number == ticket_number,
        ).first()
        if existing_ticket:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ticket #{ticket_number} has already been allocated to another subscriber",
            )

        # 7. Check total capacity
        current_count = db.query(ChitMembership).filter(ChitMembership.chit_group_id == group_id).count()
        if current_count >= max_tickets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Group is full ({current_count}/{max_tickets} tickets allocated)",
            )

        # Create membership
        membership = ChitMembership(
            chit_group_id=group_id,
            user_id=user_id,
            ticket_number=ticket_number,
            status=MembershipStatus.ACTIVE,
        )
        db.add(membership)
        db.commit()
        db.refresh(membership)
        return membership

    @classmethod
    def remove_member(cls, db: Session, group_id: uuid.UUID, membership_id: uuid.UUID) -> None:
        """Remove a member from a group during enrollment phase."""
        membership = db.query(ChitMembership).filter(
            ChitMembership.id == membership_id,
            ChitMembership.chit_group_id == group_id,
        ).first()
        if not membership:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")

        group = db.query(ChitGroup).filter(ChitGroup.id == group_id).first()
        if group.status not in [ChitGroupStatus.DRAFT, ChitGroupStatus.ENROLLING]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Members cannot be removed once the group has been activated",
            )

        db.delete(membership)
        db.commit()

    @classmethod
    def transition_status(
        cls,
        db: Session,
        group_id: uuid.UUID,
        new_status: ChitGroupStatus,
    ) -> ChitGroup:
        """
        Transition group lifecycle state with strict invariant validations.
        Activating a group requires 100% capacity and initializes Month 1 installments.
        """
        group = db.query(ChitGroup).filter(ChitGroup.id == group_id).first()
        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chit Group not found")

        scheme = db.query(ChitScheme).filter(ChitScheme.id == group.scheme_id).first()

        # If activating: enforce capacity invariant
        if new_status == ChitGroupStatus.ACTIVE and group.status != ChitGroupStatus.ACTIVE:
            enrolled_count = db.query(ChitMembership).filter(ChitMembership.chit_group_id == group_id).count()
            required_capacity = scheme.duration_months
            if enrolled_count < required_capacity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot activate group: Incomplete enrollment. {enrolled_count}/{required_capacity} tickets allocated.",
                )

            # Generate Month 1 Installment schedule for all tickets
            memberships = db.query(ChitMembership).filter(ChitMembership.chit_group_id == group_id).all()
            for m in memberships:
                # Check if installment already exists
                existing_inst = db.query(Installment).filter(
                    Installment.chit_membership_id == m.id,
                    Installment.month_number == 1,
                ).first()
                if not existing_inst:
                    inst = Installment(
                        chit_group_id=group.id,
                        chit_membership_id=m.id,
                        month_number=1,
                        due_date=group.start_date,
                        gross_amount=scheme.monthly_installment,
                        dividend_amount=Decimal("0.00"),
                        penalty_amount=Decimal("0.00"),
                        net_due_amount=scheme.monthly_installment,
                        paid_amount=Decimal("0.00"),
                        status=InstallmentStatus.UNPAID,
                    )
                    db.add(inst)

            # Schedule Month 1 Auction
            existing_auction = db.query(Auction).filter(
                Auction.chit_group_id == group.id,
                Auction.month_number == 1,
            ).first()
            if not existing_auction:
                auction = Auction(
                    chit_group_id=group.id,
                    month_number=1,
                    scheduled_at=datetime.combine(
                        group.start_date,
                        group.auction_time,
                    ).replace(tzinfo=timezone.utc),
                    status=AuctionStatus.SCHEDULED,
                    is_foreman_month=scheme.foreman_month_one_reserved,
                )
                db.add(auction)

        group.status = new_status
        db.commit()
        db.refresh(group)
        return group
