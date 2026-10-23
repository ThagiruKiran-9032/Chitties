from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_timed_token,
    decode_token,
)
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.organization import Organization
from app.models.user import User, UserRole, KYCStatus
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserProfileResponse,
    EmailVerifyRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MessageResponse,
)
from app.services.email_service import EmailService

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])


@router.post("/seed-demo", summary="Seed initial demo organization, users, and circles")
def seed_demo():
    """Initializes or verifies demo accounts, active chit circle, and live auction."""
    from app.db.seed import seed_database
    seed_database()
    return {"message": "Demo data ready"}


@router.post(
    "/register",
    response_model=UserProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new subscriber account",
)
def register(
    payload: UserRegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Onboard a new subscriber account.
    Hashes password with bcrypt, initializes KYC state,
    and sends a verification token via SMTP.
    """
    # Check if email is already registered
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists",
        )

    # Validate organization if provided
    if payload.organization_id:
        org = db.query(Organization).filter(Organization.id == payload.organization_id).first()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Specified organization does not exist",
            )

    new_user = User(
        organization_id=payload.organization_id,
        branch_id=payload.branch_id,
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        password_hash=get_password_hash(payload.password),
        role=UserRole.SUBSCRIBER,
        kyc_status=KYCStatus.PENDING,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Generate timed verification token and dispatch via SMTP
    verify_token = create_timed_token(
        payload={"sub": str(new_user.id), "email": new_user.email},
        purpose="email_verify",
        expires_delta=timedelta(hours=24),
    )
    EmailService.send_verification_email(
        to_email=new_user.email,
        full_name=new_user.full_name,
        token=verify_token,
    )

    return new_user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive JWT access token",
)
def login(
    payload: UserLoginRequest,
    db: Session = Depends(get_db),
):
    """
    Authenticate with email and password.
    Returns signed JWT access token containing identity and role claims.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Please contact support.",
        )

    token_claims = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "org_id": str(user.organization_id) if user.organization_id else None,
        "branch_id": str(user.branch_id) if user.branch_id else None,
    }
    access_token = create_access_token(token_claims)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        user=user,
    )


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Retrieve authenticated user profile and roles",
)
def get_me(current_user: User = Depends(get_current_user)):
    """Return profile and role data of the currently authenticated user."""
    return current_user


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    summary="Verify user email address using token",
)
def verify_email(
    payload: EmailVerifyRequest,
    db: Session = Depends(get_db),
):
    """Verify an account email using the token received via SMTP."""
    try:
        data = decode_token(payload.token)
        if data.get("purpose") != "email_verify":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token purpose",
            )
        user_id = data.get("sub")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired email verification token",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User associated with token not found",
        )

    user.kyc_status = KYCStatus.VERIFIED
    db.commit()

    return MessageResponse(
        message="Email successfully verified. Your account is now active.",
        status="success",
    )


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request a password reset link via SMTP",
)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Initiate password recovery. Generates a 1-hour reset token
    and sends the recovery email via SMTP.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if user and user.is_active:
        reset_token = create_timed_token(
            payload={"sub": str(user.id), "email": user.email},
            purpose="password_reset",
            expires_delta=timedelta(hours=1),
        )
        delivered = EmailService.send_password_reset_email(
            to_email=user.email,
            full_name=user.full_name,
            token=reset_token,
        )
        return MessageResponse(
            message="If an active account exists with this email, a password reset link has been dispatched.",
            status="success",
            email_delivered=delivered,
        )

    # Standard security practice: Avoid account enumeration
    return MessageResponse(
        message="If an active account exists with this email, a password reset link has been dispatched.",
        status="success",
        email_delivered=False,
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Set new password using verified reset token",
)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Update user password after validating the reset token."""
    try:
        data = decode_token(payload.token)
        if data.get("purpose") != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token purpose",
            )
        user_id = data.get("sub")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.password_hash = get_password_hash(payload.new_password)
    db.commit()

    return MessageResponse(
        message="Password has been successfully reset. You may now log in with your new password.",
        status="success",
    )
