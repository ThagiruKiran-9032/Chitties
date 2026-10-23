import calendar
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.auction import Auction, AuctionStatus, Bid
from app.models.chit_group import ChitGroup, ChitGroupStatus
from app.models.chit_scheme import ChitScheme
from app.models.membership import ChitMembership, MembershipStatus
from app.models.installment import Installment, InstallmentStatus
from app.models.user import User, UserRole
from app.schemas.auction import (
    AuctionDetailResponse,
    AuctionSummaryResponse,
    AuctionCloseResponse,
    BidResponse,
)
from app.services.auction_ws_manager import auction_ws_manager


def add_months(sourcedate: date, months: int) -> date:
    """Helper to safely advance calendar dates across month/leap year boundaries."""
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


class AuctionService:
    """
    Core Chit Fund reverse discount bidding, settlement math, FCFS sequencing,
    and dividend ledger allocation engine.
    """

    @staticmethod
    def _to_summary(db: Session, a: Auction) -> AuctionSummaryResponse:
        highest_bid = (
            db.query(Bid)
            .filter(Bid.auction_id == a.id, Bid.is_valid == True)
            .order_by(Bid.bid_discount_amount.desc(), Bid.timestamp.asc())
            .first()
        )
        highest_val = highest_bid.bid_discount_amount if highest_bid else None

        winning_ticket = None
        winning_name = None
        if a.winning_membership:
            winning_ticket = a.winning_membership.ticket_number
            winning_name = a.winning_membership.user.full_name if a.winning_membership.user else None

        return AuctionSummaryResponse(
            id=a.id,
            chit_group_id=a.chit_group_id,
            month_number=a.month_number,
            scheduled_at=a.scheduled_at,
            opened_at=a.opened_at,
            closed_at=a.closed_at,
            status=a.status,
            is_foreman_month=a.is_foreman_month,
            winning_membership_id=a.winning_membership_id,
            winning_ticket_number=winning_ticket,
            winning_member_name=winning_name,
            winning_bid_discount=a.winning_bid_discount,
            foreman_commission=a.foreman_commission,
            total_dividend_pool=a.total_dividend_pool,
            dividend_per_ticket=a.dividend_per_ticket,
            net_payable_installment=a.net_payable_installment,
            current_highest_bid=highest_val,
        )

    @staticmethod
    def list_organization_auctions(
        db: Session,
        current_user: User,
        status_filter: Optional[AuctionStatus] = None,
    ) -> List[AuctionSummaryResponse]:
        """List auctions across the current user's organization."""
        query = db.query(Auction).join(ChitGroup, Auction.chit_group_id == ChitGroup.id)
        if current_user.role != UserRole.SUPER_ADMIN:
            query = query.filter(ChitGroup.organization_id == current_user.organization_id)

        canonical_role = current_user.role.canonical
        if canonical_role == UserRole.MANAGER:
            query = query.filter(ChitGroup.manager_id == current_user.id)
        elif canonical_role == UserRole.MEMBER:
            enrolled_group_ids = [
                m[0] for m in db.query(ChitMembership.chit_group_id)
                .filter(ChitMembership.user_id == current_user.id)
                .all()
            ]
            query = query.filter(ChitGroup.id.in_(enrolled_group_ids))

        if status_filter:
            query = query.filter(Auction.status == status_filter)

        auctions = query.order_by(Auction.scheduled_at.desc()).limit(100).all()
        return [AuctionService._to_summary(db, a) for a in auctions]

    @staticmethod
    def get_group_auctions(
        db: Session,
        group_id: uuid.UUID,
        current_user: User,
    ) -> List[AuctionSummaryResponse]:
        """List all monthly round auctions for a chit group with winning subscriber metadata."""
        group = db.query(ChitGroup).filter(ChitGroup.id == group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chit Group not found.",
            )

        from app.services.authz_service import AuthorizationService
        AuthorizationService.check_group_access(current_user, group, db, write=False)

        auctions = (
            db.query(Auction)
            .filter(Auction.chit_group_id == group_id)
            .order_by(Auction.month_number.asc())
            .all()
        )

        return [AuctionService._to_summary(db, a) for a in auctions]

    @staticmethod
    def get_auction_detail(
        db: Session,
        auction_id: uuid.UUID,
        current_user: User,
    ) -> AuctionDetailResponse:
        """Fetch deep auction details, bounds, user ticket context, and recent bid history."""
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Auction not found.",
            )

        group = db.query(ChitGroup).filter(ChitGroup.id == auction.chit_group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated Chit Group not found.",
            )

        from app.services.authz_service import AuthorizationService
        AuthorizationService.check_group_access(current_user, group, db, write=False)

        scheme = db.query(ChitScheme).filter(ChitScheme.id == group.scheme_id).first()

        # Compute discount bounds
        min_discount = (scheme.total_value * (scheme.min_bid_discount_pct / Decimal(100))).quantize(Decimal("0.01"))
        max_discount = (scheme.total_value * (scheme.max_bid_discount_pct / Decimal(100))).quantize(Decimal("0.01"))

        # Find user's ticket in this group (if subscriber)
        user_membership = (
            db.query(ChitMembership)
            .filter(
                ChitMembership.chit_group_id == group.id,
                ChitMembership.user_id == current_user.id,
            )
            .first()
        )

        user_membership_id = user_membership.id if user_membership else None
        user_ticket_number = user_membership.ticket_number if user_membership else None
        user_is_prized = (user_membership.status == MembershipStatus.PRIZED) if user_membership else False

        # Query all recent bids ordered by timestamp desc
        bids = (
            db.query(Bid)
            .filter(Bid.auction_id == auction.id, Bid.is_valid == True)
            .order_by(Bid.timestamp.desc())
            .limit(50)
            .all()
        )

        recent_bids = []
        for b in bids:
            recent_bids.append(
                BidResponse(
                    id=b.id,
                    auction_id=b.auction_id,
                    chit_membership_id=b.chit_membership_id,
                    ticket_number=b.membership.ticket_number if b.membership else None,
                    bidder_name=b.membership.user.full_name if (b.membership and b.membership.user) else None,
                    bid_discount_amount=b.bid_discount_amount,
                    timestamp=b.timestamp,
                    is_valid=b.is_valid,
                )
            )

        # Current highest bid
        highest_bid = (
            db.query(Bid)
            .filter(Bid.auction_id == auction.id, Bid.is_valid == True)
            .order_by(Bid.bid_discount_amount.desc(), Bid.timestamp.asc())
            .first()
        )
        highest_val = highest_bid.bid_discount_amount if highest_bid else None

        winning_ticket = None
        winning_name = None
        if auction.winning_membership:
            winning_ticket = auction.winning_membership.ticket_number
            winning_name = auction.winning_membership.user.full_name if auction.winning_membership.user else None

        return AuctionDetailResponse(
            id=auction.id,
            chit_group_id=auction.chit_group_id,
            month_number=auction.month_number,
            scheduled_at=auction.scheduled_at,
            opened_at=auction.opened_at,
            closed_at=auction.closed_at,
            status=auction.status,
            is_foreman_month=auction.is_foreman_month,
            winning_membership_id=auction.winning_membership_id,
            winning_ticket_number=winning_ticket,
            winning_member_name=winning_name,
            winning_bid_discount=auction.winning_bid_discount,
            foreman_commission=auction.foreman_commission,
            total_dividend_pool=auction.total_dividend_pool,
            dividend_per_ticket=auction.dividend_per_ticket,
            net_payable_installment=auction.net_payable_installment,
            current_highest_bid=highest_val,
            group_code=group.group_code,
            total_value=scheme.total_value,
            duration_months=scheme.duration_months,
            monthly_installment=scheme.monthly_installment,
            min_bid_discount=min_discount,
            max_bid_discount=max_discount,
            user_membership_id=user_membership_id,
            user_ticket_number=user_ticket_number,
            user_is_prized=user_is_prized,
            recent_bids=recent_bids,
        )

    @staticmethod
    async def start_auction(
        db: Session,
        auction_id: uuid.UUID,
        current_user: User,
    ) -> Auction:
        """Start a live auction session and notify connected WebSocket subscribers."""
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Auction not found.",
            )

        group = db.query(ChitGroup).filter(ChitGroup.id == auction.chit_group_id).first()
        from app.services.authz_service import AuthorizationService, Permission
        AuthorizationService.check_group_access(current_user, group, db, write=True)

        if not AuthorizationService.has_permission(current_user, Permission.MANAGE_AUCTIONS):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only authorized staff or admins may start an auction session.",
            )

        if auction.status != AuctionStatus.SCHEDULED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot start auction in {auction.status.value} status. Only SCHEDULED auctions can be opened.",
            )

        # Check that prior months are finalized/closed
        if auction.month_number > 1:
            prior_open = (
                db.query(Auction)
                .filter(
                    Auction.chit_group_id == group.id,
                    Auction.month_number < auction.month_number,
                    Auction.status != AuctionStatus.CLOSED,
                    Auction.status != AuctionStatus.FINALIZED,
                )
                .first()
            )
            if prior_open:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot start Round {auction.month_number}: Round {prior_open.month_number} is still open.",
                )

        auction.status = AuctionStatus.OPEN
        auction.opened_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(auction)

        # Broadcast event
        await auction_ws_manager.broadcast(
            auction.id,
            {
                "type": "AUCTION_STARTED",
                "auction_id": str(auction.id),
                "month_number": auction.month_number,
                "opened_at": auction.opened_at.isoformat(),
            },
        )

        return auction

    @staticmethod
    async def place_bid(
        db: Session,
        auction_id: uuid.UUID,
        bid_discount_amount: Decimal,
        current_user: User,
        membership_id: Optional[uuid.UUID] = None,
    ) -> Bid:
        """
        Submits and validates a reverse discount bid.
        Enforces discount bounds, FCFS ceiling rank, prior-winner exclusion, and monotonic timestamps.
        """
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Auction not found.",
            )

        if auction.status != AuctionStatus.OPEN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Auction is {auction.status.value}. Bids can only be submitted during an OPEN session.",
            )

        if auction.is_foreman_month:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This round is reserved for the Foreman and is not open to subscriber bidding.",
            )

        group = db.query(ChitGroup).filter(ChitGroup.id == auction.chit_group_id).first()
        if current_user.role != UserRole.SUPER_ADMIN and group.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied.",
            )

        # Resolve subscriber membership
        if membership_id:
            membership = db.query(ChitMembership).filter(ChitMembership.id == membership_id).first()
            if not membership or membership.chit_group_id != group.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Specified ticket does not belong to this chit group.",
                )
            # If current user is a subscriber, ensure they own this ticket
            if current_user.role == UserRole.SUBSCRIBER and membership.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Subscribers may only place bids for their own ticket.",
                )
        else:
            membership = (
                db.query(ChitMembership)
                .filter(
                    ChitMembership.chit_group_id == group.id,
                    ChitMembership.user_id == current_user.id,
                )
                .first()
            )
            if not membership:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not an enrolled ticket holder in this chit group.",
                )

        # Prized subscriber exclusion rule
        if membership.status == MembershipStatus.PRIZED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ticket #{membership.ticket_number} is already prized and cannot bid in subsequent rounds.",
            )

        if membership.status != MembershipStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ticket #{membership.ticket_number} is not active ({membership.status.value}).",
            )

        scheme = db.query(ChitScheme).filter(ChitScheme.id == group.scheme_id).first()
        min_discount = (scheme.total_value * (scheme.min_bid_discount_pct / Decimal(100))).quantize(Decimal("0.01"))
        max_discount = (scheme.total_value * (scheme.max_bid_discount_pct / Decimal(100))).quantize(Decimal("0.01"))

        # Discount boundary checks
        if bid_discount_amount < min_discount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bid discount ₹{bid_discount_amount:,.2f} is below the minimum allowed floor of ₹{min_discount:,.2f}.",
            )

        if bid_discount_amount > max_discount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bid discount ₹{bid_discount_amount:,.2f} exceeds the maximum statutory cap of ₹{max_discount:,.2f}.",
            )

        # FCFS and Highest Bid Validation
        highest_bid = (
            db.query(Bid)
            .filter(Bid.auction_id == auction.id, Bid.is_valid == True)
            .order_by(Bid.bid_discount_amount.desc(), Bid.timestamp.asc())
            .first()
        )

        if highest_bid:
            if highest_bid.bid_discount_amount >= max_discount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"The maximum discount cap of ₹{max_discount:,.2f} has already been claimed by Ticket #{highest_bid.membership.ticket_number} under FCFS rules.",
                )
            if bid_discount_amount <= highest_bid.bid_discount_amount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Bid discount must strictly exceed current highest bid of ₹{highest_bid.bid_discount_amount:,.2f}.",
                )

        # Persist bid
        bid = Bid(
            auction_id=auction.id,
            chit_membership_id=membership.id,
            bid_discount_amount=bid_discount_amount,
            is_valid=True,
        )
        db.add(bid)

        auction.winning_bid_discount = bid_discount_amount
        db.commit()
        db.refresh(bid)

        # Broadcast to room
        await auction_ws_manager.broadcast(
            auction.id,
            {
                "type": "NEW_BID",
                "bid": {
                    "id": str(bid.id),
                    "auction_id": str(bid.auction_id),
                    "chit_membership_id": str(membership.id),
                    "ticket_number": membership.ticket_number,
                    "bidder_name": membership.user.full_name,
                    "bid_discount_amount": str(bid.bid_discount_amount),
                    "timestamp": bid.timestamp.isoformat(),
                },
            },
        )

        return bid

    @staticmethod
    async def close_auction(
        db: Session,
        auction_id: uuid.UUID,
        current_user: User,
    ) -> AuctionCloseResponse:
        """
        Closes and finalizes an auction round.
        Computes Foreman Commission, Dividend Pool, Dividend Per Ticket,
        marks the winning subscriber as PRIZED, and generates/updates next month's installment ledger.
        """
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Auction not found.",
            )

        group = db.query(ChitGroup).filter(ChitGroup.id == auction.chit_group_id).first()
        from app.services.authz_service import AuthorizationService, Permission
        AuthorizationService.check_group_access(current_user, group, db, write=True)

        if not AuthorizationService.has_permission(current_user, Permission.MANAGE_AUCTIONS):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only authorized staff or admins may conclude an auction.",
            )

        if auction.status != AuctionStatus.OPEN and not (auction.is_foreman_month and auction.status == AuctionStatus.SCHEDULED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot close auction in status {auction.status.value}.",
            )

        scheme = db.query(ChitScheme).filter(ChitScheme.id == group.scheme_id).first()
        V = scheme.total_value
        N = Decimal(str(scheme.duration_months))

        winning_membership = None
        winning_discount = Decimal("0.00")

        if auction.is_foreman_month:
            # Foreman entitlement
            foreman_comm_pct = scheme.foreman_commission_pct
            foreman_commission = (V * (foreman_comm_pct / Decimal(100))).quantize(Decimal("0.01"))
            winning_discount = foreman_commission
            prize_amount = V - winning_discount
            total_dividend_pool = Decimal("0.00")
            dividend_per_ticket = Decimal("0.00")
            net_payable = scheme.monthly_installment
        else:
            # Look up winning bid via FCFS composite index
            winning_bid = (
                db.query(Bid)
                .filter(Bid.auction_id == auction.id, Bid.is_valid == True)
                .order_by(Bid.bid_discount_amount.desc(), Bid.timestamp.asc())
                .first()
            )
            if not winning_bid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot close auction without any bids. Place at least one bid or handle non-bid fallback.",
                )

            winning_discount = winning_bid.bid_discount_amount
            winning_membership = winning_bid.membership
            winning_membership.status = MembershipStatus.PRIZED
            auction.winning_membership_id = winning_membership.id

            foreman_comm_pct = scheme.foreman_commission_pct
            foreman_commission = (V * (foreman_comm_pct / Decimal(100))).quantize(Decimal("0.01"))
            prize_amount = V - winning_discount
            total_dividend_pool = max(Decimal("0.00"), winning_discount - foreman_commission)
            dividend_per_ticket = (total_dividend_pool / N).quantize(Decimal("0.01"))
            net_payable = (scheme.monthly_installment - dividend_per_ticket).quantize(Decimal("0.01"))

        # Update Auction record
        auction.status = AuctionStatus.CLOSED
        auction.closed_at = datetime.now(timezone.utc)
        auction.winning_bid_discount = winning_discount
        auction.foreman_commission = foreman_commission
        auction.total_dividend_pool = total_dividend_pool
        auction.dividend_per_ticket = dividend_per_ticket
        auction.net_payable_installment = net_payable

        # Ledger Distribution: Generate / Update next month's installment schedule
        next_month = auction.month_number + 1
        installments_updated = 0

        if next_month <= scheme.duration_months:
            due_date = add_months(group.start_date, next_month - 1)
            memberships = db.query(ChitMembership).filter(ChitMembership.chit_group_id == group.id).all()

            for m in memberships:
                inst = (
                    db.query(Installment)
                    .filter(
                        Installment.chit_membership_id == m.id,
                        Installment.month_number == next_month,
                    )
                    .first()
                )
                if inst:
                    inst.dividend_amount = dividend_per_ticket
                    inst.net_due_amount = (inst.gross_amount - dividend_per_ticket).quantize(Decimal("0.01"))
                else:
                    inst = Installment(
                        chit_group_id=group.id,
                        chit_membership_id=m.id,
                        month_number=next_month,
                        due_date=due_date,
                        gross_amount=scheme.monthly_installment,
                        dividend_amount=dividend_per_ticket,
                        penalty_amount=Decimal("0.00"),
                        net_due_amount=(scheme.monthly_installment - dividend_per_ticket).quantize(Decimal("0.01")),
                        paid_amount=Decimal("0.00"),
                        status=InstallmentStatus.UNPAID,
                    )
                    db.add(inst)
                installments_updated += 1

            # Check if next month auction exists
            next_auction = (
                db.query(Auction)
                .filter(
                    Auction.chit_group_id == group.id,
                    Auction.month_number == next_month,
                )
                .first()
            )
            if not next_auction:
                auction_sched_time = datetime.combine(due_date, group.auction_time).replace(tzinfo=timezone.utc)
                next_auction = Auction(
                    chit_group_id=group.id,
                    month_number=next_month,
                    scheduled_at=auction_sched_time,
                    status=AuctionStatus.SCHEDULED,
                    is_foreman_month=False,
                )
                db.add(next_auction)

            group.current_month = next_month
        else:
            # All rounds finished
            group.status = ChitGroupStatus.COMPLETED

        db.commit()
        db.refresh(auction)

        winner_name = winning_membership.user.full_name if (winning_membership and winning_membership.user) else None
        winner_ticket = winning_membership.ticket_number if winning_membership else None

        # Broadcast auction closed event
        await auction_ws_manager.broadcast(
            auction.id,
            {
                "type": "AUCTION_CLOSED",
                "auction_id": str(auction.id),
                "month_number": auction.month_number,
                "winner_ticket": winner_ticket,
                "winner_name": winner_name,
                "winning_bid_discount": str(winning_discount),
                "prize_amount": str(prize_amount),
                "dividend_per_ticket": str(dividend_per_ticket),
                "net_payable_installment": str(net_payable),
            },
        )

        return AuctionCloseResponse(
            auction_id=auction.id,
            month_number=auction.month_number,
            winner_membership_id=auction.winning_membership_id,
            winner_ticket_number=winner_ticket,
            winner_name=winner_name,
            winning_bid_discount=winning_discount,
            prize_amount=prize_amount,
            foreman_commission=foreman_commission,
            total_dividend_pool=total_dividend_pool,
            dividend_per_ticket=dividend_per_ticket,
            net_payable_installment=net_payable,
            next_month_installments_generated=installments_updated,
        )
