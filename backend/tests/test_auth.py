import uuid
from datetime import timedelta
import pytest
from fastapi import status, HTTPException

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_timed_token,
    decode_token,
)
from app.dependencies.auth import enforce_tenant_isolation
from app.models.organization import Organization, OrgStatus
from app.models.user import User, UserRole, KYCStatus
from app.services.email_service import EmailService


def test_password_hashing():
    """Verify bcrypt hashes are salted uniquely and verify accurately."""
    raw_pw = "StrongP@ssw0rd2026"
    hash1 = get_password_hash(raw_pw)
    hash2 = get_password_hash(raw_pw)

    # Different salts must yield different hashes
    assert hash1 != hash2
    assert verify_password(raw_pw, hash1) is True
    assert verify_password(raw_pw, hash2) is True
    assert verify_password("WrongPassword", hash1) is False


def test_jwt_creation_and_decoding():
    """Verify JWT token encoding and decoding."""
    user_id = str(uuid.uuid4())
    token = create_access_token(
        data={"sub": user_id, "role": "SUBSCRIBER", "org_id": str(uuid.uuid4())},
        expires_delta=timedelta(minutes=15),
    )
    payload = decode_token(token)
    assert payload["sub"] == user_id
    assert payload["role"] == "SUBSCRIBER"
    assert "exp" in payload


def test_jwt_expired_token():
    """Verify expired token causes decode failure."""
    token = create_access_token(
        data={"sub": str(uuid.uuid4())},
        expires_delta=timedelta(seconds=-10),  # In the past
    )
    with pytest.raises(Exception):
        decode_token(token)


def test_register_subscriber(client, db_session):
    """Test public subscriber registration endpoint."""
    email = f"register_{uuid.uuid4().hex[:6]}@example.com"
    payload = {
        "full_name": "New Subscriber",
        "email": email,
        "phone": "+919876500001",
        "password": "SecurePassword123!",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == email
    assert data["role"] == UserRole.SUBSCRIBER
    assert data["kyc_status"] == KYCStatus.PENDING
    assert "password" not in data
    assert "password_hash" not in data


def test_register_duplicate_email(client, db_session):
    """Test duplicate registration with same email is rejected with HTTP 400."""
    email = f"dup_{uuid.uuid4().hex[:6]}@example.com"
    payload = {
        "full_name": "First User",
        "email": email,
        "phone": "+919876500002",
        "password": "Password123!",
    }
    r1 = client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == status.HTTP_201_CREATED

    r2 = client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in r2.json()["detail"]


def test_login_success(client, db_session):
    """Test successful login returns JWT access token."""
    email = f"login_{uuid.uuid4().hex[:6]}@example.com"
    raw_pw = "ValidPassword123!"
    user = User(
        full_name="Login Tester",
        email=email,
        phone="+919876500003",
        password_hash=get_password_hash(raw_pw),
        role=UserRole.SUBSCRIBER,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post("/api/v1/auth/login", json={"email": email, "password": raw_pw})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == email


def test_login_invalid_password(client, db_session):
    """Test wrong password returns HTTP 401."""
    email = f"wrong_{uuid.uuid4().hex[:6]}@example.com"
    user = User(
        full_name="Wrong PW Tester",
        email=email,
        phone="+919876500004",
        password_hash=get_password_hash("CorrectPassword1!"),
        role=UserRole.SUBSCRIBER,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post("/api/v1/auth/login", json={"email": email, "password": "WrongPassword!"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid email or password" in response.json()["detail"]


def test_login_deactivated_user(client, db_session):
    """Test deactivated account cannot log in (HTTP 403)."""
    email = f"deactive_{uuid.uuid4().hex[:6]}@example.com"
    raw_pw = "ValidPass123!"
    user = User(
        full_name="Inactive User",
        email=email,
        phone="+919876500005",
        password_hash=get_password_hash(raw_pw),
        role=UserRole.SUBSCRIBER,
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post("/api/v1/auth/login", json={"email": email, "password": raw_pw})
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "deactivated" in response.json()["detail"]


def test_get_me_authenticated(client, db_session):
    """Test /me endpoint with valid Bearer token."""
    email = f"me_{uuid.uuid4().hex[:6]}@example.com"
    user = User(
        full_name="Profile User",
        email=email,
        phone="+919876500006",
        password_hash=get_password_hash("pw"),
        role=UserRole.BRANCH_MANAGER,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == email
    assert data["role"] == "BRANCH_MANAGER"


def test_get_me_unauthorized(client):
    """Test calling /me without credentials returns HTTP 401."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_rbac_admin_route_forbidden_for_subscriber(client, db_session):
    """Test subscriber role is barred from admin-only endpoint (HTTP 403)."""
    subscriber = User(
        full_name="Normal Sub",
        email=f"sub_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919876500007",
        password_hash=get_password_hash("pw"),
        role=UserRole.SUBSCRIBER,
        is_active=True,
    )
    db_session.add(subscriber)
    db_session.commit()

    token = create_access_token({"sub": str(subscriber.id), "role": subscriber.role.value})
    response = client.get("/api/v1/test/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Operation not permitted" in response.json()["detail"]


def test_rbac_admin_route_allowed_for_org_admin(client, db_session):
    """Test org admin role is permitted on admin-only endpoint (HTTP 200)."""
    admin = User(
        full_name="Org Boss",
        email=f"boss_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919876500008",
        password_hash=get_password_hash("pw"),
        role=UserRole.ORG_ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    token = create_access_token({"sub": str(admin.id), "role": admin.role.value})
    response = client.get("/api/v1/test/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Admin authorization granted"


def test_tenant_isolation_guard():
    """Verify tenant isolation enforcement between different organizations."""
    org_a = uuid.uuid4()
    org_b = uuid.uuid4()

    user_a = User(
        id=uuid.uuid4(),
        organization_id=org_a,
        role=UserRole.BRANCH_MANAGER,
        full_name="Manager A",
        email="a@test.com",
        phone="123",
        password_hash="pw",
    )
    super_admin = User(
        id=uuid.uuid4(),
        organization_id=None,
        role=UserRole.SUPER_ADMIN,
        full_name="Super Admin",
        email="sa@test.com",
        phone="000",
        password_hash="pw",
    )

    # User A accessing Org A -> Permitted (no exception)
    enforce_tenant_isolation(org_a, user_a)

    # User A attempting to access Org B -> Blocked with HTTP 403
    with pytest.raises(HTTPException) as exc_info:
        enforce_tenant_isolation(org_b, user_a)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    # SuperAdmin accessing any organization -> Permitted
    enforce_tenant_isolation(org_a, super_admin)
    enforce_tenant_isolation(org_b, super_admin)


def test_email_verification_workflow(client, db_session):
    """Test verifying account with timed verification token."""
    user = User(
        full_name="Unverified User",
        email=f"verify_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919876500009",
        password_hash="pw",
        role=UserRole.SUBSCRIBER,
        kyc_status=KYCStatus.PENDING,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    token = create_timed_token(
        payload={"sub": str(user.id), "email": user.email},
        purpose="email_verify",
        expires_delta=timedelta(hours=24),
    )

    response = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "success"

    db_session.refresh(user)
    assert user.kyc_status == KYCStatus.VERIFIED


def test_password_recovery_and_reset_workflow(client, db_session):
    """Test full forgot-password and reset-password flow."""
    email = f"reset_{uuid.uuid4().hex[:6]}@example.com"
    old_pw = "OldPassword123!"
    new_pw = "BrandNewPassword2026!"

    user = User(
        full_name="Reset User",
        email=email,
        phone="+919876500010",
        password_hash=get_password_hash(old_pw),
        role=UserRole.SUBSCRIBER,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    # Step 1: Request reset link
    r1 = client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert r1.status_code == status.HTTP_200_OK

    # Step 2: Generate valid reset token
    reset_token = create_timed_token(
        payload={"sub": str(user.id), "email": user.email},
        purpose="password_reset",
        expires_delta=timedelta(hours=1),
    )

    # Step 3: Submit new password
    r2 = client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": new_pw},
    )
    assert r2.status_code == status.HTTP_200_OK

    # Step 4: Verify old password fails and new password succeeds
    login_old = client.post("/api/v1/auth/login", json={"email": email, "password": old_pw})
    assert login_old.status_code == status.HTTP_401_UNAUTHORIZED

    login_new = client.post("/api/v1/auth/login", json={"email": email, "password": new_pw})
    assert login_new.status_code == status.HTTP_200_OK
    assert "access_token" in login_new.json()


def test_smtp_live_email_send():
    """Verify live SMTP email transmission using configured Gmail credentials."""
    success = EmailService.send_email(
        to_email="cluelescompany@gmail.com",
        subject="Chitties Phase 3 SMTP Verification Test",
        text_content="This is an automated test confirming Gmail SMTP integration in Chitties Phase 3.",
    )
    assert success is True
