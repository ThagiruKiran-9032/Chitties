import uuid
from datetime import datetime
from decimal import Decimal
from typing import List

from sqlalchemy import String, Boolean, Integer, Numeric, DateTime, ForeignKey, CheckConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ChitScheme(Base):
    """
    Blueprint configuration for chit fund offerings.
    Defines financial terms, statutory commission, and discount bidding caps.
    """
    __tablename__ = "chit_schemes"

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
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    total_value: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )
    duration_months: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    monthly_installment: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )
    foreman_commission_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("5.00"),
    )
    max_bid_discount_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("30.00"),
    )
    min_bid_discount_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("5.00"),
    )
    foreman_month_one_reserved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="chit_schemes",
    )
    chit_groups: Mapped[List["ChitGroup"]] = relationship(
        "ChitGroup",
        back_populates="scheme",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("total_value > 0", name="ck_chit_schemes_total_value_positive"),
        CheckConstraint("duration_months > 0", name="ck_chit_schemes_duration_positive"),
        CheckConstraint("monthly_installment > 0", name="ck_chit_schemes_installment_positive"),
        CheckConstraint("foreman_commission_pct >= 0 AND foreman_commission_pct <= 20", name="ck_chit_schemes_commission_range"),
        CheckConstraint("max_bid_discount_pct >= foreman_commission_pct", name="ck_chit_schemes_max_discount_valid"),
    )
