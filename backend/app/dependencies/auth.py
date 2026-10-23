import uuid
from typing import List, Callable, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User, UserRole

security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Extract and cryptographically verify the JWT bearer token from HTTP Authorization header.
    Returns the authenticated User model instance.
    """
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials are required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth.credentials
    try:
        payload = decode_token(token)
        user_id_str: str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload is missing subject claim",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, tampered, or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with this token no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account has been deactivated",
        )

    return user


from app.services.authz_service import AuthorizationService, Permission


def require_roles(allowed_roles: List[UserRole]) -> Callable:
    """
    Role-Based Access Control (RBAC) dependency factory.
    Enforces that current_user holds one of the specified roles (supports canonical matching).
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role in allowed_roles:
            return current_user
        if allowed_roles != [UserRole.SUPER_ADMIN]:
            allowed_canonicals = {r.canonical for r in allowed_roles if r != UserRole.SUPER_ADMIN}
            if current_user.role.canonical in allowed_canonicals:
                return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Operation not permitted. Required roles: {[r.value for r in allowed_roles]}",
        )

    return role_checker


def require_permission(permission: Permission) -> Callable:
    """
    Fine-grained permission checking dependency.
    Validates current_user against centralized authorization rules.
    """
    def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        AuthorizationService.enforce_permission(current_user, permission)
        return current_user

    return permission_checker


def enforce_tenant_isolation(
    target_org_id: uuid.UUID,
    current_user: User,
) -> None:
    """
    Enforce multi-tenant isolation.
    SuperAdmins bypass tenant checks. All other users are restricted to their own organization.
    """
    if current_user.role == UserRole.SUPER_ADMIN:
        return

    if current_user.organization_id != target_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cannot query or manipulate records of another organization",
        )
