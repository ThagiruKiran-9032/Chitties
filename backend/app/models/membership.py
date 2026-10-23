import enum
import uuid
from datetime import datetime
from typing import List

from sqlalchemy import Integer, DateTime, Enum, ForeignKey, UniqueConstraint, CheckConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MembershipStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PRIZED = "PRIZED"
    DEFAULTED = "DEFAULTED"
    SUBSTITUTED = "SUBSTITUTED"


class ChitMembership(Base):
    """
    Subscribed ticket held by a Member in a ChitGroup.
    Strictly 1 ticket per user per chit group is enforced via unique constraint.
    """
    __tablename__ = "chit_memberships"

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
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    ticket_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[MembershipStatus] = mapped_column(
        Enum(MembershipStatus, name="membership_status_enum"),
        nullable=False,
        default=MembershipStatus.ACTIVE,
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    chit_group: Mapped["ChitGroup"] = relationship(
        "ChitGroup",
        back_populates="memberships",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="memberships",
    )
    bids: Mapped[List["Bid"]] = relationship(
        "Bid",
        back_populates="membership",
        cascade="all, delete-orphan",
    )
    installments: Mapped[List["Installment"]] = relationship(
        "Installment",
        back_populates="membership",
        cascade="all, delete-orphan",
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment",
        back_populates="membership",
    )
    payouts: Mapped[List["Payout"]] = relationship(
        "Payout",
        back_populates="membership",
    )

    __table_args__ = (
        # Strictly single ticket per user per group
        UniqueConstraint("chit_group_id", "user_id", name="uq_memberships_group_user"),
        # Unique ticket numbers within each chit group
        UniqueConstraint("chit_group_id", "ticket_number", name="uq_memberships_group_ticket"),
        CheckConstraint("ticket_number >= 1", name="ck_memberships_ticket_number_positive"),
    )
