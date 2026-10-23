import math
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_roles, require_permission, enforce_tenant_isolation
from app.models.chit_scheme import ChitScheme
from app.models.chit_group import ChitGroup, ChitGroupStatus
from app.models.membership import ChitMembership
from app.models.organization import Branch
from app.models.user import User, UserRole
from app.schemas.common import PaginatedResponse
from app.schemas.chit_group import (
    ChitGroupCreate,
    ChitGroupAssignManagerRequest,
    ChitGroupStatusUpdate,
    EnrollmentRequest,
    ChitMembershipResponse,
    ChitGroupResponse,
)
from app.services.authz_service import AuthorizationService, Permission
from app.services.chit_group_service import ChitGroupService

router = APIRouter(prefix="/groups", tags=["Chit Groups"])


@router.post(
    "",
    response_model=ChitGroupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Launch a new Chit Group circle (Admin only)",
)
@router.post(
    "/",
    response_model=ChitGroupResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_group(
    payload: ChitGroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CREATE_CHIT_GROUPS)),
):
    """Instantiate a running chit group circle from an approved scheme."""
    org_id = current_user.organization_id

    # Validate scheme
    scheme = db.query(ChitScheme).filter(ChitScheme.id == payload.scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chit Scheme not found")
    if current_user.role != UserRole.SUPER_ADMIN and scheme.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Scheme belongs to another organization")

    # Validate branch
    branch = db.query(Branch).filter(Branch.id == payload.branch_id).first()
    if not branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    if current_user.role != UserRole.SUPER_ADMIN and branch.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Branch belongs to another organization")

    # Validate manager if provided
    manager = None
    if payload.manager_id:
        manager = db.query(User).filter(User.id == payload.manager_id).first()
        if not manager or (current_user.role != UserRole.SUPER_ADMIN and manager.organization_id != org_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned manager not found in organization")

    # Check unique group code in tenant
    existing = db.query(ChitGroup).filter(
        ChitGroup.organization_id == org_id,
        ChitGroup.group_code == payload.group_code,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Group code '{payload.group_code}' already exists in your organization",
        )

    group = ChitGroup(
        organization_id=org_id,
        branch_id=payload.branch_id,
        manager_id=payload.manager_id,
        scheme_id=payload.scheme_id,
        group_code=payload.group_code,
        start_date=payload.start_date,
        end_date=payload.end_date,
        current_month=1,
        auction_day_of_month=payload.auction_day_of_month,
        auction_time=payload.auction_time,
        status=ChitGroupStatus.DRAFT,
    )
    db.add(group)
    db.commit()
    db.refresh(group)

    return ChitGroupResponse(
        id=group.id,
        organization_id=group.organization_id,
        branch_id=group.branch_id,
        manager_id=group.manager_id,
        manager_name=manager.full_name if manager else None,
        scheme_id=group.scheme_id,
        group_code=group.group_code,
        start_date=group.start_date,
        end_date=group.end_date,
        current_month=group.current_month,
        auction_day_of_month=group.auction_day_of_month,
        auction_time=group.auction_time,
        status=group.status,
        created_at=group.created_at,
        enrolled_count=0,
        total_capacity=scheme.duration_months,
    )


@router.post(
    "/{id}/assign-manager",
    response_model=ChitGroupResponse,
    summary="Assign a Manager to a Chit Group circle (Admin only)",
)
def assign_manager(
    id: uuid.UUID,
    payload: ChitGroupAssignManagerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ASSIGN_GROUP_MANAGERS)),
):
    """Admin assigns an authorized Manager to manage this specific chit circle."""
    group = db.query(ChitGroup).filter(ChitGroup.id == id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    enforce_tenant_isolation(group.organization_id, current_user)

    manager = db.query(User).filter(User.id == payload.manager_id).first()
    if not manager or (current_user.role != UserRole.SUPER_ADMIN and manager.organization_id != group.organization_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Designated manager not found in organization")

    if manager.role.canonical != UserRole.MANAGER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User '{manager.full_name}' holds role '{manager.role.value}', which cannot be assigned as a Group Manager.",
        )

    group.manager_id = payload.manager_id
    db.commit()
    db.refresh(group)

    enrolled = db.query(ChitMembership).filter(ChitMembership.chit_group_id == group.id).count()
    scheme = db.query(ChitScheme).filter(ChitScheme.id == group.scheme_id).first()

    return ChitGroupResponse(
        id=group.id,
        organization_id=group.organization_id,
        branch_id=group.branch_id,
        manager_id=group.manager_id,
        manager_name=manager.full_name,
        scheme_id=group.scheme_id,
        group_code=group.group_code,
        start_date=group.start_date,
        end_date=group.end_date,
        current_month=group.current_month,
        auction_day_of_month=group.auction_day_of_month,
        auction_time=group.auction_time,
        status=group.status,
        created_at=group.created_at,
        enrolled_count=enrolled,
        total_capacity=scheme.duration_months if scheme else 0,
    )


@router.get(
    "",
    response_model=PaginatedResponse[ChitGroupResponse],
    summary="List chit groups with role-based scoping",
)
@router.get(
    "/",
    response_model=PaginatedResponse[ChitGroupResponse],
    include_in_schema=False,
)
def list_groups(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    branch_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[ChitGroupStatus] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve chit groups with capacity and enrolled counts:
    - Admin & Accountant: All groups in organization.
    - Manager: ONLY groups assigned to this Manager (manager_id == current_user.id).
    - Member: ONLY groups where member holds an active ticket.
    """
    query = db.query(ChitGroup)
    if current_user.role != UserRole.SUPER_ADMIN:
        query = query.filter(ChitGroup.organization_id == current_user.organization_id)

    canonical_role = current_user.role.canonical

    if canonical_role == UserRole.MANAGER:
        # Restrict manager strictly to assigned groups (or branch fallback if manager_id is not yet set)
        query = query.filter(
            (ChitGroup.manager_id == current_user.id) |
            ((ChitGroup.manager_id == None) & (ChitGroup.branch_id == current_user.branch_id))
        )
    elif canonical_role == UserRole.MEMBER:
        # Restrict member strictly to groups they hold a ticket in
        enrolled_group_ids = [
            m[0] for m in db.query(ChitMembership.chit_group_id)
            .filter(ChitMembership.user_id == current_user.id)
            .all()
        ]
        query = query.filter(ChitGroup.id.in_(enrolled_group_ids))
    elif branch_id:
        query = query.filter(ChitGroup.branch_id == branch_id)

    if status_filter:
        query = query.filter(ChitGroup.status == status_filter)
    if search:
        query = query.filter(ChitGroup.group_code.ilike(f"%{search}%"))

    total = query.count()
    groups = query.order_by(ChitGroup.start_date.desc()).offset((page - 1) * size).limit(size).all()
    total_pages = math.ceil(total / size) if size > 0 else 0

    items = []
    for g in groups:
        enrolled = db.query(ChitMembership).filter(ChitMembership.chit_group_id == g.id).count()
        scheme = db.query(ChitScheme).filter(ChitScheme.id == g.scheme_id).first()
        items.append(
            ChitGroupResponse(
                id=g.id,
                organization_id=g.organization_id,
                branch_id=g.branch_id,
                manager_id=g.manager_id,
                manager_name=g.manager.full_name if g.manager else None,
                scheme_id=g.scheme_id,
                group_code=g.group_code,
                start_date=g.start_date,
                end_date=g.end_date,
                current_month=g.current_month,
                auction_day_of_month=g.auction_day_of_month,
                auction_time=g.auction_time,
                status=g.status,
                created_at=g.created_at,
                enrolled_count=enrolled,
                total_capacity=scheme.duration_months if scheme else 0,
            )
        )

    return PaginatedResponse(
        items=items,
        total_items=total,
        page=page,
        page_size=size,
        total_pages=total_pages,
    )


@router.get(
    "/{id}",
    response_model=ChitGroupResponse,
    summary="Get single chit group details with authorization scoping",
)
def get_group(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve group details and capacity. Enforces role-based group scoping."""
    group = db.query(ChitGroup).filter(ChitGroup.id == id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    AuthorizationService.check_group_access(current_user, group, db, write=False)

    enrolled = db.query(ChitMembership).filter(ChitMembership.chit_group_id == group.id).count()
    scheme = db.query(ChitScheme).filter(ChitScheme.id == group.scheme_id).first()

    return ChitGroupResponse(
        id=group.id,
        organization_id=group.organization_id,
        branch_id=group.branch_id,
        manager_id=group.manager_id,
        manager_name=group.manager.full_name if group.manager else None,
        scheme_id=group.scheme_id,
        group_code=group.group_code,
        start_date=group.start_date,
        end_date=group.end_date,
        current_month=group.current_month,
        auction_day_of_month=group.auction_day_of_month,
        auction_time=group.auction_time,
        status=group.status,
        created_at=group.created_at,
        enrolled_count=enrolled,
        total_capacity=scheme.duration_months if scheme else 0,
    )


@router.patch(
    "/{id}/status",
    response_model=ChitGroupResponse,
    summary="Transition chit group lifecycle state",
)
def update_group_status(
    id: uuid.UUID,
    payload: ChitGroupStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Transition group state (e.g. DRAFT -> ENROLLING -> ACTIVE)."""
    group = db.query(ChitGroup).filter(ChitGroup.id == id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    AuthorizationService.check_group_access(current_user, group, db, write=True)

    updated_group = ChitGroupService.transition_status(db, id, payload.status)
    enrolled = db.query(ChitMembership).filter(ChitMembership.chit_group_id == id).count()
    scheme = db.query(ChitScheme).filter(ChitScheme.id == updated_group.scheme_id).first()

    return ChitGroupResponse(
        id=updated_group.id,
        organization_id=updated_group.organization_id,
        branch_id=updated_group.branch_id,
        manager_id=updated_group.manager_id,
        manager_name=updated_group.manager.full_name if updated_group.manager else None,
        scheme_id=updated_group.scheme_id,
        group_code=updated_group.group_code,
        start_date=updated_group.start_date,
        end_date=updated_group.end_date,
        current_month=updated_group.current_month,
        auction_day_of_month=updated_group.auction_day_of_month,
        auction_time=updated_group.auction_time,
        status=updated_group.status,
        created_at=updated_group.created_at,
        enrolled_count=enrolled,
        total_capacity=scheme.duration_months if scheme else 0,
    )


@router.post(
    "/{id}/enroll",
    response_model=ChitMembershipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a verified subscriber to a ticket",
)
def enroll_subscriber(
    id: uuid.UUID,
    payload: EnrollmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Enroll subscriber with KYC checks, capacity checks, and single-ticket rules."""
    group = db.query(ChitGroup).filter(ChitGroup.id == id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    AuthorizationService.check_group_access(current_user, group, db, write=True)

    membership = ChitGroupService.enroll_member(
        db=db,
        group_id=id,
        user_id=payload.user_id,
        ticket_number=payload.ticket_number,
        caller=current_user,
    )
    subscriber = db.query(User).filter(User.id == payload.user_id).first()

    return ChitMembershipResponse(
        id=membership.id,
        chit_group_id=membership.chit_group_id,
        user_id=membership.user_id,
        ticket_number=membership.ticket_number,
        status=membership.status,
        enrolled_at=membership.enrolled_at,
        full_name=subscriber.full_name if subscriber else None,
        email=subscriber.email if subscriber else None,
        phone=subscriber.phone if subscriber else None,
    )


@router.delete(
    "/{id}/enroll/{membership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member from group (enrollment phase only)",
)
def remove_subscriber(
    id: uuid.UUID,
    membership_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """De-allocate a ticket before group activation."""
    group = db.query(ChitGroup).filter(ChitGroup.id == id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    AuthorizationService.check_group_access(current_user, group, db, write=True)

    ChitGroupService.remove_member(db=db, group_id=id, membership_id=membership_id)
    return None


@router.get(
    "/{id}/memberships",
    response_model=List[ChitMembershipResponse],
    summary="List all allocated tickets in a chit group",
)
def list_group_memberships(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List memberships and ticket numbers in group with role-based scoping."""
    group = db.query(ChitGroup).filter(ChitGroup.id == id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    AuthorizationService.check_group_access(current_user, group, db, write=False)

    memberships = (
        db.query(ChitMembership, User)
        .join(User, ChitMembership.user_id == User.id)
        .filter(ChitMembership.chit_group_id == id)
        .order_by(ChitMembership.ticket_number.asc())
        .all()
    )

    results = []
    for m, u in memberships:
        results.append(
            ChitMembershipResponse(
                id=m.id,
                chit_group_id=m.chit_group_id,
                user_id=m.user_id,
                ticket_number=m.ticket_number,
                status=m.status,
                enrolled_at=m.enrolled_at,
                full_name=u.full_name,
                email=u.email,
                phone=u.phone,
            )
        )
    return results
