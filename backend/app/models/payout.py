import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    String,
    Text,
    Numeric,
    DateTime,
    Enum,
    ForeignKey,
    CheckConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PayoutStatus(str, enum.Enum):
    PENDING_SURETY = "PENDING_SURETY"
    SURETY_APPROVED = "SURETY_APPROVED"
    DISBURSED = "DISBURSED"
    CANCELLED = "CANCELLED"


class SuretyType(str, enum.Enum):
    GUARANTOR = "GUARANTOR"
    PROPERTY_COLLATERAL = "PROPERTY_COLLATERAL"
    SALARY_CERTIFICATE = "SALARY_CERTIFICATE"
    FIXED_DEPOSIT = "FIXED_DEPOSIT"


class SuretyStatus(str, enum.Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class Payout(Base):
    """
    Prize money payout disbursement to an auction winner.
    Enforces two-step verification workflow: PENDING_SURETY -> SURETY_APPROVED -> DISBURSED.
    """
    __tablename__ = "payouts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    auction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auctions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    chit_membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chit_memberships.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    gross_prize_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )
    foreman_charges_deducted: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    arrears_deducted: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    net_disbursed_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )
    disbursement_status: Mapped[PayoutStatus] = mapped_column(
        Enum(PayoutStatus, name="payout_status_enum"),
        nullable=False,
        default=PayoutStatus.PENDING_SURETY,
    )
    disbursement_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    disbursed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    auction: Mapped["Auction"] = relationship(
        "Auction",
        back_populates="payout",
    )
    membership: Mapped["ChitMembership"] = relationship(
        "ChitMembership",
        back_populates="payouts",
    )
    sureties: Mapped[List["Surety"]] = relationship(
        "Surety",
        back_populates="payout",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("gross_prize_amount > 0", name="ck_payouts_gross_prize_positive"),
        CheckConstraint("net_disbursed_amount >= 0", name="ck_payouts_net_disbursed_positive"),
    )


class Surety(Base):
    """
    Collateral or guarantor security provided by a prized subscriber
    to secure the remaining future installments of a chit group.
    """
    __tablename__ = "sureties"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    payout_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payouts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    surety_type: Mapped[SuretyType] = mapped_column(
        Enum(SuretyType, name="surety_type_enum"),
        nullable=False,
    )
    guarantor_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    guarantor_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    document_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    verification_status: Mapped[SuretyStatus] = mapped_column(
        Enum(SuretyStatus, name="surety_status_enum"),
        nullable=False,
        default=SuretyStatus.PENDING,
    )
    verified_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    payout: Mapped["Payout"] = relationship(
        "Payout",
        back_populates="sureties",
    )
    verified_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[verified_by_user_id],
    )
