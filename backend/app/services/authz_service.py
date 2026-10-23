import enum
import uuid
from typing import Set, Dict, Optional, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.chit_group import ChitGroup
from app.models.membership import ChitMembership


class Permission(str, enum.Enum):
    VIEW_ORG_DASHBOARD = "VIEW_ORG_DASHBOARD"
    MANAGE_USERS = "MANAGE_USERS"
    MANAGE_ORG_SETTINGS = "MANAGE_ORG_SETTINGS"
    CREATE_CHIT_GROUPS = "CREATE_CHIT_GROUPS"
    ASSIGN_GROUP_MANAGERS = "ASSIGN_GROUP_MANAGERS"
    VIEW_GROUP_MEMBERS = "VIEW_GROUP_MEMBERS"
    VIEW_INSTALLMENT_SCHEDULES = "VIEW_INSTALLMENT_SCHEDULES"
    RECORD_PAYMENTS = "RECORD_PAYMENTS"
    VERIFY_RECONCILE_PAYMENTS = "VERIFY_RECONCILE_PAYMENTS"
    GENERATE_RECEIPTS = "GENERATE_RECEIPTS"
    MANAGE_AUCTIONS = "MANAGE_AUCTIONS"
    VIEW_AUCTION_RESULTS = "VIEW_AUCTION_RESULTS"
    PROCESS_PAYOUTS = "PROCESS_PAYOUTS"
    APPROVE_SENSITIVE_FINANCIAL_OPS = "APPROVE_SENSITIVE_FINANCIAL_OPS"
    VIEW_FINANCIAL_REPORTS = "VIEW_FINANCIAL_REPORTS"
    VIEW_AUDIT_LOGS = "VIEW_AUDIT_LOGS"
    VIEW_PERSONAL_PROFILE = "VIEW_PERSONAL_PROFILE"


# Deny-by-default role permission mappings
ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
    UserRole.ADMIN: {
        Permission.VIEW_ORG_DASHBOARD,
        Permission.MANAGE_USERS,
        Permission.MANAGE_ORG_SETTINGS,
        Permission.CREATE_CHIT_GROUPS,
        Permission.ASSIGN_GROUP_MANAGERS,
        Permission.VIEW_GROUP_MEMBERS,
        Permission.VIEW_INSTALLMENT_SCHEDULES,
        Permission.RECORD_PAYMENTS,
        Permission.VERIFY_RECONCILE_PAYMENTS,
        Permission.GENERATE_RECEIPTS,
        Permission.MANAGE_AUCTIONS,
        Permission.VIEW_AUCTION_RESULTS,
        Permission.PROCESS_PAYOUTS,
        Permission.APPROVE_SENSITIVE_FINANCIAL_OPS,
        Permission.VIEW_FINANCIAL_REPORTS,
        Permission.VIEW_AUDIT_LOGS,
        Permission.VIEW_PERSONAL_PROFILE,
    },
    UserRole.MANAGER: {
        Permission.MANAGE_USERS,
        Permission.VIEW_GROUP_MEMBERS,
        Permission.VIEW_INSTALLMENT_SCHEDULES,
        Permission.GENERATE_RECEIPTS,
        Permission.MANAGE_AUCTIONS,
        Permission.VIEW_AUCTION_RESULTS,
        Permission.PROCESS_PAYOUTS,
        Permission.VIEW_FINANCIAL_REPORTS,
        Permission.VIEW_PERSONAL_PROFILE,
    },
    UserRole.ACCOUNTANT: {
        Permission.VIEW_INSTALLMENT_SCHEDULES,
        Permission.RECORD_PAYMENTS,
        Permission.VERIFY_RECONCILE_PAYMENTS,
        Permission.GENERATE_RECEIPTS,
        Permission.VIEW_AUCTION_RESULTS,
        Permission.PROCESS_PAYOUTS,
        Permission.VIEW_FINANCIAL_REPORTS,
        Permission.VIEW_PERSONAL_PROFILE,
    },
    UserRole.MEMBER: {
        Permission.VIEW_INSTALLMENT_SCHEDULES,
        Permission.RECORD_PAYMENTS,
        Permission.GENERATE_RECEIPTS,
        Permission.VIEW_AUCTION_RESULTS,
        Permission.VIEW_PERSONAL_PROFILE,
    },
}


class AuthorizationService:
    """
    Centralized, audit-compliant authorization engine enforcing RBAC,
    group-level manager scoping, member data isolation, and financial dual-control.
    """

    @staticmethod
    def get_canonical_role(user: User) -> UserRole:
        """Resolve legacy alias roles to the 4 canonical roles."""
        return user.role.canonical

    @staticmethod
    def has_permission(user: User, permission: Permission) -> bool:
        """Check if user's canonical role holds a given permission."""
        if not user.is_active:
            return False
        canonical_role = user.role.canonical
        allowed_permissions = ROLE_PERMISSIONS.get(canonical_role, set())
        return permission in allowed_permissions

    @staticmethod
    def enforce_permission(user: User, permission: Permission) -> None:
        """Raise HTTP 403 if user lacks required permission."""
        if not AuthorizationService.has_permission(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation '{permission.value}' not permitted for role '{user.role.value}'.",
            )

    @staticmethod
    def check_group_access(
        user: User,
        group: ChitGroup,
        db: Session,
        write: bool = False,
    ) -> None:
        """
        Enforce organization tenant isolation and role-specific group access:
        - Admin: Full access across organization.
        - Manager: Only assigned groups (group.manager_id == user.id). Returns 404 if unassigned.
        - Accountant: Read-only access across organization. Cannot write/edit groups.
        - Member: Read-only access only if enrolled in this group. Returns 404 if not enrolled.
        """
        # Tenant isolation
        if user.role != UserRole.SUPER_ADMIN and group.organization_id != user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chit Group not found.",
            )

        canonical_role = user.role.canonical

        if canonical_role == UserRole.ADMIN:
            return

        if canonical_role == UserRole.MANAGER:
            # Manager is restricted to groups assigned to them
            if group.manager_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chit Group not found.",
                )
            return

        if canonical_role == UserRole.ACCOUNTANT:
            if write:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Accountants are not permitted to configure or modify chit groups.",
                )
            return

        if canonical_role == UserRole.MEMBER:
            if write:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Members are not permitted to configure or modify chit groups.",
                )
            # Verify member holds a ticket in this group
            is_enrolled = (
                db.query(ChitMembership)
                .filter(
                    ChitMembership.chit_group_id == group.id,
                    ChitMembership.user_id == user.id,
                )
                .first()
            )
            if not is_enrolled:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chit Group not found.",
                )
            return

        # Deny-by-default
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to chit group is denied.",
        )

    @staticmethod
    def check_member_data_access(
        current_user: User,
        target_user: User,
        db: Session,
    ) -> None:
        """
        Enforce subscriber data isolation:
        - Admin: Full member directory access within organization.
        - Manager: Can only access members enrolled in groups assigned to this Manager.
        - Accountant: Can view members for payment/reconciliation purposes.
        - Member: Can ONLY view their own profile/records.
        """
        if current_user.role != UserRole.SUPER_ADMIN and target_user.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cross-tenant access denied: Member belongs to another organization.",
            )

        canonical_role = current_user.role.canonical

        if canonical_role == UserRole.ADMIN:
            return

        if canonical_role == UserRole.MEMBER:
            if current_user.id != target_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Cannot access other members' records.",
                )
            return

        if canonical_role == UserRole.MANAGER:
            # Check if target_user shares an assigned group with this Manager
            shares_group = (
                db.query(ChitMembership)
                .join(ChitGroup, ChitMembership.chit_group_id == ChitGroup.id)
                .filter(
                    ChitGroup.manager_id == current_user.id,
                    ChitMembership.user_id == target_user.id,
                )
                .first()
            )
            if not shares_group and current_user.id != target_user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Member not found.",
                )
            return

        if canonical_role == UserRole.ACCOUNTANT:
            return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to member records is denied.",
        )

    @staticmethod
    def check_payment_record_permission(
        current_user: User,
        membership_user_id: uuid.UUID,
    ) -> None:
        """
        Enforce payment recording responsibilities:
        - Manager: FORBIDDEN from recording payments (must not touch financial transactions).
        - Member: Can only record payments for their OWN subscribed ticket.
        - Accountant / Admin: Permitted to record payments across the organization.
        """
        canonical_role = current_user.role.canonical

        if canonical_role == UserRole.MANAGER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Managers are strictly restricted from recording financial payment transactions.",
            )

        if canonical_role == UserRole.MEMBER:
            if current_user.id != membership_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Subscribers may only record payments for their own subscribed ticket.",
                )
            return

        if canonical_role in (UserRole.ADMIN, UserRole.ACCOUNTANT):
            return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted.",
        )

    @staticmethod
    def check_payout_disbursement_permission(current_user: User) -> None:
        """
        Dual-control rule:
        Prize money disbursement authorization requires Admin approval.
        Accountants prepare and process claim details, but Admin must approve disbursement.
        """
        canonical_role = current_user.role.canonical
        if canonical_role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Dual-control requirement: Prize money disbursement requires Admin authorization.",
            )
