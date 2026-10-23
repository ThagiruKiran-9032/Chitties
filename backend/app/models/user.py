import enum
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, Boolean, DateTime, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserRole(str, enum.Enum):
    # Canonical 4 Roles per RBAC Master Specification
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    ACCOUNTANT = "ACCOUNTANT"
    MEMBER = "MEMBER"

    # Compatibility Aliases
    SUPER_ADMIN = "SUPER_ADMIN"
    ORG_ADMIN = "ORG_ADMIN"
    BRANCH_MANAGER = "BRANCH_MANAGER"
    COLLECTION_AGENT = "COLLECTION_AGENT"
    SUBSCRIBER = "SUBSCRIBER"

    @property
    def canonical(self) -> "UserRole":
        """Normalize legacy aliases into the 4 canonical roles."""
        if self in (UserRole.ADMIN, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN):
            return UserRole.ADMIN
        if self in (UserRole.MANAGER, UserRole.BRANCH_MANAGER):
            return UserRole.MANAGER
        if self in (UserRole.ACCOUNTANT, UserRole.COLLECTION_AGENT):
            return UserRole.ACCOUNTANT
        return UserRole.MEMBER


class KYCStatus(str, enum.Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class User(Base):
    """
    Platform User Entity across all personas.
    SuperAdmins have organization_id=None.
    Tenant staff and subscribers are bound to an organization.
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    branch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum"),
        nullable=False,
    )
    kyc_status: Mapped[KYCStatus] = mapped_column(
        Enum(KYCStatus, name="kyc_status_enum"),
        nullable=False,
        default=KYCStatus.PENDING,
    )
    kyc_document_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    kyc_document_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
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
    organization: Mapped[Optional["Organization"]] = relationship(
        "Organization",
        back_populates="users",
    )
    branch: Mapped[Optional["Branch"]] = relationship(
        "Branch",
        back_populates="users",
    )
    memberships: Mapped[List["ChitMembership"]] = relationship(
        "ChitMembership",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    recorded_payments: Mapped[List["Payment"]] = relationship(
        "Payment",
        back_populates="recorded_by_user",
        foreign_keys="Payment.recorded_by_user_id",
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "phone", name="uq_users_org_phone"),
    )
