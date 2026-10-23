import uuid
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, Any

from sqlalchemy import (
    String,
    Date,
    DateTime,
    Numeric,
    Text,
    ForeignKey,
    Enum as SQLEnum,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DepositType(str, Enum):
    FIXED_DEPOSIT = "FIXED_DEPOSIT"
    BANK_GUARANTEE = "BANK_GUARANTEE"
    GOVERNMENT_SECURITIES = "GOVERNMENT_SECURITIES"


class LienStatus(str, Enum):
    PENDING = "PENDING"
    PLEDGED = "PLEDGED"
    RELEASED = "RELEASED"


class FilingType(str, Enum):
    FORM_I_SANCTION = "FORM_I_SANCTION"
    FORM_II_AGREEMENT = "FORM_II_AGREEMENT"
    FORM_XIV_MINUTES = "FORM_XIV_MINUTES"
    FORM_XXI_STATEMENT = "FORM_XXI_STATEMENT"


class FilingStatus(str, Enum):
    DRAFT = "DRAFT"
    FILED = "FILED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    REJECTED = "REJECTED"


class SecurityDeposit(Base):
    """
    Chit Funds Act 1982 Section 20 Statutory Foreman Security Deposit.
    Mandates 100% chit value deposited in an approved bank / Registrar name before commencement.
    """
    __tablename__ = "security_deposits"

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
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chit_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    deposit_type: Mapped[DepositType] = mapped_column(
        SQLEnum(DepositType, name="deposit_type_enum"),
        nullable=False,
        default=DepositType.FIXED_DEPOSIT,
    )
    bank_name: Mapped[str] = mapped_column(String(150), nullable=False)
    account_or_fdr_number: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    deposit_date: Mapped[date] = mapped_column(Date, nullable=False)
    maturity_date: Mapped[date] = mapped_column(Date, nullable=False)
    registrar_order_reference: Mapped[str] = mapped_column(String(100), nullable=False)
    lien_status: Mapped[LienStatus] = mapped_column(
        SQLEnum(LienStatus, name="lien_status_enum"),
        nullable=False,
        default=LienStatus.PENDING,
        index=True,
    )
    remarks: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    group: Mapped["ChitGroup"] = relationship("ChitGroup")


class RegistrarFiling(Base):
    """
    Statutory filings lodged with the State Registrar of Chits.
    Covers Prior Sanction (Form I), Chit Agreement (Form II),
    Auction Minutes (Form XIV), and Balance Sheet / P&L (Form XXI).
    """
    __tablename__ = "registrar_filings"

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
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chit_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    auction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auctions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    form_type: Mapped[FilingType] = mapped_column(
        SQLEnum(FilingType, name="filing_type_enum"),
        nullable=False,
        index=True,
    )
    filing_reference_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )
    filed_date: Mapped[date] = mapped_column(Date, nullable=False)
    registrar_office_name: Mapped[str] = mapped_column(String(150), nullable=False)
    acknowledgment_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[FilingStatus] = mapped_column(
        SQLEnum(FilingStatus, name="filing_status_enum"),
        nullable=False,
        default=FilingStatus.DRAFT,
        index=True,
    )
    metadata_payload: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    group: Mapped["ChitGroup"] = relationship("ChitGroup")
    auction: Mapped[Optional["Auction"]] = relationship("Auction")
