import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Integer,
    Numeric,
    DateTime,
    Enum,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AuctionStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    FINALIZED = "FINALIZED"
    CANCELLED = "CANCELLED"


class Auction(Base):
    """
    Monthly reverse auction held for a ChitGroup.
    Tracks status, winning subscriber, dividend pool, and installment calculations.
    """
    __tablename__ = "auctions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    chit_group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chit_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    month_number: Mapped[int] = mapped_column(Integer, nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[AuctionStatus] = mapped_column(
        Enum(AuctionStatus, name="auction_status_enum"),
        nullable=False,
        default=AuctionStatus.SCHEDULED,
    )
    is_foreman_month: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    winning_membership_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chit_memberships.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    winning_bid_discount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    foreman_commission: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    total_dividend_pool: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    dividend_per_ticket: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    net_payable_installment: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    chit_group: Mapped["ChitGroup"] = relationship(
        "ChitGroup",
        back_populates="auctions",
    )
    winning_membership: Mapped[Optional["ChitMembership"]] = relationship(
        "ChitMembership",
        foreign_keys=[winning_membership_id],
    )
    bids: Mapped[List["Bid"]] = relationship(
        "Bid",
        back_populates="auction",
        cascade="all, delete-orphan",
    )
    payout: Mapped[Optional["Payout"]] = relationship(
        "Payout",
        back_populates="auction",
        uselist=False,
    )

    __table_args__ = (
        UniqueConstraint("chit_group_id", "month_number", name="uq_auctions_group_month"),
        CheckConstraint("month_number >= 1", name="ck_auctions_month_positive"),
        CheckConstraint("winning_bid_discount >= 0", name="ck_auctions_discount_positive"),
        CheckConstraint("foreman_commission >= 0", name="ck_auctions_commission_positive"),
        CheckConstraint("total_dividend_pool >= 0", name="ck_auctions_dividend_positive"),
    )


class Bid(Base):
    """
    Live discount bids placed by subscribers during an active auction session.
    First-Come, First-Served tie-breaking queries utilize composite indexing.
    """
    __tablename__ = "bids"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    auction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auctions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chit_membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chit_memberships.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    bid_discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    auction: Mapped["Auction"] = relationship(
        "Auction",
        back_populates="bids",
    )
    membership: Mapped["ChitMembership"] = relationship(
        "ChitMembership",
        back_populates="bids",
    )

    __table_args__ = (
        CheckConstraint("bid_discount_amount > 0", name="ck_bids_discount_positive"),
        # Optimized index for finding highest discount with earliest timestamp (FCFS)
        Index(
            "ix_bids_auction_rank",
            "auction_id",
            "bid_discount_amount",
            "timestamp",
        ),
    )
