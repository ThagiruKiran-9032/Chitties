import math
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_roles, enforce_tenant_isolation
from app.models.organization import Organization, OrgStatus
from app.models.user import User, UserRole
from app.schemas.common import PaginatedResponse
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
)

router = APIRouter(prefix="/organizations", tags=["Organizations & Tenants"])


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Provision a new Chit Fund Organization (SuperAdmin only)",
)
@router.post(
    "/",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_organization(
    payload: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.SUPER_ADMIN])),
):
    """Platform SuperAdmin creates a new independent Chit Fund Company tenant."""
    existing = db.query(Organization).filter(
        Organization.registration_number == payload.registration_number
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An organization with this registration number already exists",
        )

    org = Organization(
        name=payload.name,
        registration_number=payload.registration_number,
        tax_id=payload.tax_id,
        state_registration_details=payload.state_registration_details,
        status=payload.status,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@router.get(
    "",
    response_model=PaginatedResponse[OrganizationResponse],
    summary="List all organizations (SuperAdmin only)",
)
@router.get(
    "/",
    response_model=PaginatedResponse[OrganizationResponse],
    include_in_schema=False,
)
def list_organizations(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    status_filter: Optional[OrgStatus] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.SUPER_ADMIN])),
):
    """Retrieve paginated list of all tenant organizations."""
    query = db.query(Organization)
    if status_filter:
        query = query.filter(Organization.status == status_filter)
    if search:
        query = query.filter(Organization.name.ilike(f"%{search}%"))

    total = query.count()
    items = query.order_by(Organization.name.asc()).offset((page - 1) * size).limit(size).all()
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
    response_model=OrganizationResponse,
    summary="Retrieve organization details",
)
def get_organization(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get single organization profile with tenant isolation enforcement."""
    enforce_tenant_isolation(id, current_user)
    org = db.query(Organization).filter(Organization.id == id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return org


@router.patch(
    "/{id}",
    response_model=OrganizationResponse,
    summary="Update organization details",
)
def update_organization(
    id: uuid.UUID,
    payload: OrganizationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Modify organization details (SuperAdmin or authorized Org Admin)."""
    enforce_tenant_isolation(id, current_user)
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SuperAdmin or Org Admin can modify organization details",
        )

    org = db.query(Organization).filter(Organization.id == id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(org, field, value)

    db.commit()
    db.refresh(org)
    return org
