import math
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_roles, enforce_tenant_isolation
from app.models.organization import Branch, BranchStatus
from app.models.user import User, UserRole
from app.schemas.common import PaginatedResponse
from app.schemas.branch import (
    BranchCreate,
    BranchUpdate,
    BranchResponse,
)

router = APIRouter(prefix="/branches", tags=["Branches"])


@router.post(
    "",
    response_model=BranchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new branch office (Org Admin only)",
)
@router.post(
    "/",
    response_model=BranchResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_branch(
    payload: BranchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ORG_ADMIN])),
):
    """Org Admin creates a physical branch office under their organization."""
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin user is not associated with an organization",
        )

    # Check unique branch code within this organization
    existing = db.query(Branch).filter(
        Branch.organization_id == org_id,
        Branch.branch_code == payload.branch_code,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Branch code '{payload.branch_code}' already exists in your organization",
        )

    branch = Branch(
        organization_id=org_id,
        branch_code=payload.branch_code,
        name=payload.name,
        address=payload.address,
        phone=payload.phone,
        status=payload.status,
    )
    db.add(branch)
    db.commit()
    db.refresh(branch)
    return branch


@router.get(
    "",
    response_model=PaginatedResponse[BranchResponse],
    summary="List branches with pagination and filters",
)
@router.get(
    "/",
    response_model=PaginatedResponse[BranchResponse],
    include_in_schema=False,
)
def list_branches(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    status_filter: Optional[BranchStatus] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN, UserRole.BRANCH_MANAGER])),
):
    """Retrieve branches belonging to caller's organization."""
    query = db.query(Branch)
    if current_user.role != UserRole.SUPER_ADMIN:
        query = query.filter(Branch.organization_id == current_user.organization_id)

    if status_filter:
        query = query.filter(Branch.status == status_filter)
    if search:
        query = query.filter(Branch.name.ilike(f"%{search}%") | Branch.branch_code.ilike(f"%{search}%"))

    total = query.count()
    items = query.order_by(Branch.name.asc()).offset((page - 1) * size).limit(size).all()
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
    response_model=BranchResponse,
    summary="Retrieve single branch",
)
def get_branch(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get branch details with tenant check."""
    branch = db.query(Branch).filter(Branch.id == id).first()
    if not branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")

    enforce_tenant_isolation(branch.organization_id, current_user)
    return branch


@router.patch(
    "/{id}",
    response_model=BranchResponse,
    summary="Update branch details (Org Admin only)",
)
def update_branch(
    id: uuid.UUID,
    payload: BranchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ORG_ADMIN])),
):
    """Org Admin updates branch address, phone, or active status."""
    branch = db.query(Branch).filter(Branch.id == id).first()
    if not branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")

    enforce_tenant_isolation(branch.organization_id, current_user)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(branch, field, value)

    db.commit()
    db.refresh(branch)
    return branch
