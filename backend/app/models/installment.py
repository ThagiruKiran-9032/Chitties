import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List

from sqlalchemy import (
    Integer,
    Numeric,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InstallmentStatus(str, enum.Enum):
    UNPAID = "UNPAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    OVERDUE = "OVERDUE"


class Installment(Base):
    """
    Monthly installment obligation for a specific subscribed ticket.
    Tracks gross amount, applied dividend discounts, penalties, and payment progress.
    """
    __tablename__ = "installments"

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
    chit_membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chit_memberships.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    month_number: Mapped[int] = mapped_column(Integer, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )
    dividend_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    penalty_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    net_due_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    status: Mapped[InstallmentStatus] = mapped_column(
        Enum(InstallmentStatus, name="installment_status_enum"),
        nullable=False,
        default=InstallmentStatus.UNPAID,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    chit_group: Mapped["ChitGroup"] = relationship(
        "ChitGroup",
        back_populates="installments",
    )
    membership: Mapped["ChitMembership"] = relationship(
        "ChitMembership",
        back_populates="installments",
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment",
        back_populates="installment",
    )

    __table_args__ = (
        UniqueConstraint("chit_membership_id", "month_number", name="uq_installments_ticket_month"),
        CheckConstraint("gross_amount > 0", name="ck_installments_gross_positive"),
        CheckConstraint("dividend_amount >= 0", name="ck_installments_dividend_non_negative"),
        CheckConstraint("penalty_amount >= 0", name="ck_installments_penalty_non_negative"),
        CheckConstraint("paid_amount >= 0", name="ck_installments_paid_non_negative"),
        CheckConstraint("net_due_amount >= 0", name="ck_installments_net_due_non_negative"),
    )
