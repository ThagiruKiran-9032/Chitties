import enum
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, Text, DateTime, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrgStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class BranchStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class Organization(Base):
    """
    Master Tenant Entity. Represents a licensed Chit Fund Company.
    All business data partitions on organization_id.
    """
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    registration_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    tax_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    state_registration_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[OrgStatus] = mapped_column(
        Enum(OrgStatus, name="org_status_enum"),
        nullable=False,
        default=OrgStatus.ACTIVE,
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
    branches: Mapped[List["Branch"]] = relationship(
        "Branch",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    chit_schemes: Mapped[List["ChitScheme"]] = relationship(
        "ChitScheme",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    chit_groups: Mapped[List["ChitGroup"]] = relationship(
        "ChitGroup",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment",
        back_populates="organization",
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="organization",
    )


class Branch(Base):
    """
    Administrative Branch Office operating under an Organization.
    """
    __tablename__ = "branches"

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
    branch_code: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    status: Mapped[BranchStatus] = mapped_column(
        Enum(BranchStatus, name="branch_status_enum"),
        nullable=False,
        default=BranchStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="branches",
    )
    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="branch",
    )
    chit_groups: Mapped[List["ChitGroup"]] = relationship(
        "ChitGroup",
        back_populates="branch",
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "branch_code", name="uq_branches_org_code"),
    )
