from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_permission
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.schemas.audit_log import AuditLogResponse
from app.services.authz_service import Permission

router = APIRouter(prefix="/audit-logs", tags=["Regulatory & System Audit Logs"])


@router.get("", response_model=List[AuditLogResponse])
def list_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_AUDIT_LOGS)),
):
    """
    Retrieve immutable audit trail records across the organization.
    Restricted strictly to Administrator role with VIEW_AUDIT_LOGS permission.
    """
    query = db.query(AuditLog)

    if current_user.role != UserRole.SUPER_ADMIN:
        query = query.filter(AuditLog.organization_id == current_user.organization_id)

    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)

    if action:
        query = query.filter(AuditLog.action == action)

    offset = (page - 1) * limit
    logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

    return [
        AuditLogResponse(
            id=log.id,
            organization_id=log.organization_id,
            user_id=log.user_id,
            user_name=log.user.full_name if log.user else None,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            changes_json=log.changes_json,
            ip_address=log.ip_address,
            timestamp=log.timestamp,
        )
        for log in logs
    ]
