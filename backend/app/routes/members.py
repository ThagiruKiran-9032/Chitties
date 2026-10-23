import math
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_roles, require_permission, enforce_tenant_isolation
from app.models.chit_group import ChitGroup
from app.models.membership import ChitMembership
from app.models.organization import Branch
from app.models.user import User, UserRole, KYCStatus
from app.schemas.common import PaginatedResponse
from app.schemas.member import (
    MemberCreate,
    MemberUpdate,
    KYCSubmission,
    KYCStatusUpdate,
    MemberResponse,
)
from app.services.authz_service import AuthorizationService, Permission

router = APIRouter(prefix="/members", tags=["Members & KYC"])


@router.post(
    "",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Onboard a new subscriber or staff member (Admin only)",
)
@router.post(
    "/",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def onboard_member(
    payload: MemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_USERS)),
):
    """
    Admin onboards a subscriber or employee.
    Enforces organization tenancy and role assignment rules.
    """
    org_id = current_user.organization_id
    if current_user.role != UserRole.SUPER_ADMIN and not org_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Caller has no organization")

    if current_user.role.canonical == UserRole.MANAGER:
        if payload.role not in (UserRole.MEMBER, UserRole.SUBSCRIBER):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Managers are only permitted to onboard subscriber members.",
            )

    branch_id = payload.branch_id

    # Verify branch belongs to this organization
    if branch_id:
        branch = db.query(Branch).filter(Branch.id == branch_id).first()
        if not branch:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
        if current_user.role != UserRole.SUPER_ADMIN and branch.organization_id != org_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Branch belongs to another organization")

    # Check unique email
    existing_email = db.query(User).filter(User.email == payload.email).first()
    if existing_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Check unique phone within this organization
    if org_id:
        existing_phone = db.query(User).filter(
            User.organization_id == org_id,
            User.phone == payload.phone,
        ).first()
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this phone number already exists in your organization",
            )

    new_member = User(
        organization_id=org_id,
        branch_id=branch_id,
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        password_hash=get_password_hash(payload.password),
        role=payload.role,
        kyc_status=KYCStatus.PENDING,
        kyc_document_type=payload.kyc_document_type,
        kyc_document_number=payload.kyc_document_number,
        is_active=True,
    )
    db.add(new_member)
    db.commit()
    db.refresh(new_member)
    return new_member


@router.get(
    "",
    response_model=PaginatedResponse[MemberResponse],
    summary="List members with role-based scoping",
)
@router.get(
    "/",
    response_model=PaginatedResponse[MemberResponse],
    include_in_schema=False,
)
def list_members(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    branch_id: Optional[uuid.UUID] = Query(None),
    role: Optional[UserRole] = Query(None),
    kyc_status: Optional[KYCStatus] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_GROUP_MEMBERS)),
):
    """
    Query members with role-based scoping:
    - Admin & Accountant: All members in organization.
    - Manager: ONLY members enrolled in groups assigned to this Manager.
    - Member: Forbidden from directory listing.
    """
    query = db.query(User)

    # Tenant scoping
    if current_user.role != UserRole.SUPER_ADMIN:
        query = query.filter(User.organization_id == current_user.organization_id)

    canonical_role = current_user.role.canonical

    # Manager scoping: restricted to subscribers in assigned groups
    if canonical_role == UserRole.MANAGER:
        assigned_group_subscribers = (
            db.query(ChitMembership.user_id)
            .join(ChitGroup, ChitMembership.chit_group_id == ChitGroup.id)
            .filter(ChitGroup.manager_id == current_user.id)
            .all()
        )
        allowed_user_ids = {s[0] for s in assigned_group_subscribers}
        allowed_user_ids.add(current_user.id)
        query = query.filter(User.id.in_(allowed_user_ids))
    elif branch_id:
        query = query.filter(User.branch_id == branch_id)

    if role:
        query = query.filter(User.role == role)
    if kyc_status:
        query = query.filter(User.kyc_status == kyc_status)
    if search:
        query = query.filter(
            User.full_name.ilike(f"%{search}%") | User.email.ilike(f"%{search}%") | User.phone.ilike(f"%{search}%")
        )

    total = query.count()
    items = query.order_by(User.full_name.asc()).offset((page - 1) * size).limit(size).all()
    total_pages = math.ceil(total / size) if size > 0 else 0

    return PaginatedResponse(
        items=items,
        total_items=total,
        page=page,
        page_size=size,
        total_pages=total_pages,
    )


@router.get(
    "/{id}",
    response_model=MemberResponse,
    summary="Get single member profile with data isolation",
)
def get_member(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve member profile. Enforces subscriber data isolation and manager group scoping."""
    member = db.query(User).filter(User.id == id).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    AuthorizationService.check_member_data_access(current_user, member, db)
    return member


@router.post(
    "/{id}/kyc",
    response_model=MemberResponse,
    summary="Submit KYC document details",
)
def submit_kyc(
    id: uuid.UUID,
    payload: KYCSubmission,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Subscribers submit KYC identity documents (Aadhaar, PAN, Passport)."""
    member = db.query(User).filter(User.id == id).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    # Member can only submit for themselves
    if current_user.role.canonical == UserRole.MEMBER and current_user.id != member.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if member.organization_id:
        enforce_tenant_isolation(member.organization_id, current_user)

    member.kyc_document_type = payload.kyc_document_type
    member.kyc_document_number = payload.kyc_document_number
    member.kyc_status = KYCStatus.PENDING

    db.commit()
    db.refresh(member)
    return member


@router.patch(
    "/{id}/kyc-status",
    response_model=MemberResponse,
    summary="Approve or reject member KYC status (Admin only)",
)
def update_kyc_status(
    id: uuid.UUID,
    payload: KYCStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_USERS)),
):
    """Admin verifies/rejects KYC status."""
    member = db.query(User).filter(User.id == id).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    if member.organization_id:
        enforce_tenant_isolation(member.organization_id, current_user)

    member.kyc_status = payload.status
    db.commit()
    db.refresh(member)
    return member
