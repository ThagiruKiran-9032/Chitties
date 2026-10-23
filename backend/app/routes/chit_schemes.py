import math
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_roles, enforce_tenant_isolation
from app.models.chit_scheme import ChitScheme
from app.models.user import User, UserRole
from app.schemas.common import PaginatedResponse
from app.schemas.chit_scheme import (
    ChitSchemeCreate,
    ChitSchemeUpdate,
    ChitSchemeResponse,
)

router = APIRouter(prefix="/schemes", tags=["Chit Schemes"])


@router.post(
    "",
    response_model=ChitSchemeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Chit Scheme template (Org Admin only)",
)
@router.post(
    "/",
    response_model=ChitSchemeResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_scheme(
    payload: ChitSchemeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN])),
):
    """Define a standard chit scheme template."""
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin has no assigned organization")

    scheme = ChitScheme(
        organization_id=org_id,
        name=payload.name,
        total_value=payload.total_value,
        duration_months=payload.duration_months,
        monthly_installment=payload.monthly_installment,
        foreman_commission_pct=payload.foreman_commission_pct,
        max_bid_discount_pct=payload.max_bid_discount_pct,
        min_bid_discount_pct=payload.min_bid_discount_pct,
        foreman_month_one_reserved=payload.foreman_month_one_reserved,
        is_active=payload.is_active,
    )
    db.add(scheme)
    db.commit()
    db.refresh(scheme)
    return scheme


@router.get(
    "",
    response_model=PaginatedResponse[ChitSchemeResponse],
    summary="List chit schemes with pagination",
)
@router.get(
    "/",
    response_model=PaginatedResponse[ChitSchemeResponse],
    include_in_schema=False,
)
def list_schemes(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve schemes scoped to caller's organization."""
    query = db.query(ChitScheme)
    if current_user.role != UserRole.SUPER_ADMIN:
        query = query.filter(ChitScheme.organization_id == current_user.organization_id)

    if is_active is not None:
        query = query.filter(ChitScheme.is_active == is_active)
    if search:
        query = query.filter(ChitScheme.name.ilike(f"%{search}%"))

    total = query.count()
    items = query.order_by(ChitScheme.total_value.asc()).offset((page - 1) * size).limit(size).all()
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
    response_model=ChitSchemeResponse,
    summary="Get single scheme configuration",
)
def get_scheme(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve scheme details."""
    scheme = db.query(ChitScheme).filter(ChitScheme.id == id).first()
    if not scheme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheme not found")

    enforce_tenant_isolation(scheme.organization_id, current_user)
    return scheme


@router.patch(
    "/{id}",
    response_model=ChitSchemeResponse,
    summary="Update scheme details",
)
def update_scheme(
    id: uuid.UUID,
    payload: ChitSchemeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ORG_ADMIN])),
):
    """Org Admin updates scheme name or active state."""
    scheme = db.query(ChitScheme).filter(ChitScheme.id == id).first()
    if not scheme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheme not found")

    enforce_tenant_isolation(scheme.organization_id, current_user)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(scheme, field, value)

    db.commit()
    db.refresh(scheme)
    return scheme
