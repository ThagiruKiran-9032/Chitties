import enum
import uuid
from datetime import date, time, datetime
from typing import List, Optional

from sqlalchemy import String, Integer, Date, Time, DateTime, Enum, ForeignKey, UniqueConstraint, CheckConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ChitGroupStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ENROLLING = "ENROLLING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    TERMINATED = "TERMINATED"


class ChitGroup(Base):
    """
    An operational Chit Fund Circle instantiated from a ChitScheme.
    Managed by a designated Branch, Manager, and Organization.
    """
    __tablename__ = "chit_groups"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scheme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chit_schemes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    group_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    current_month: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    auction_day_of_month: Mapped[int] = mapped_column(Integer, nullable=False)
    auction_time: Mapped[time] = mapped_column(Time, nullable=False)
    status: Mapped[ChitGroupStatus] = mapped_column(
        Enum(ChitGroupStatus, name="chit_group_status_enum"),
        nullable=False,
        default=ChitGroupStatus.DRAFT,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="chit_groups",
    )
    branch: Mapped["Branch"] = relationship(
        "Branch",
        back_populates="chit_groups",
    )
    manager: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[manager_id],
    )
    scheme: Mapped["ChitScheme"] = relationship(
        "ChitScheme",
        back_populates="chit_groups",
    )
    memberships: Mapped[List["ChitMembership"]] = relationship(
        "ChitMembership",
        back_populates="chit_group",
        cascade="all, delete-orphan",
    )
    auctions: Mapped[List["Auction"]] = relationship(
        "Auction",
        back_populates="chit_group",
        cascade="all, delete-orphan",
    )
    installments: Mapped[List["Installment"]] = relationship(
        "Installment",
        back_populates="chit_group",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "group_code", name="uq_chit_groups_org_code"),
        CheckConstraint("auction_day_of_month >= 1 AND auction_day_of_month <= 28", name="ck_chit_groups_auction_day"),
        CheckConstraint("current_month >= 1", name="ck_chit_groups_current_month"),
    )
