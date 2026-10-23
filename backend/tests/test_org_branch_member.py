import uuid
import pytest
from fastapi import status

from app.core.security import get_password_hash, create_access_token
from app.models.organization import Organization, Branch, OrgStatus, BranchStatus
from app.models.user import User, UserRole, KYCStatus


@pytest.fixture
def auth_headers():
    """Helper fixture to generate Authorization headers for any user."""
    def _headers(user: User):
        token = create_access_token({
            "sub": str(user.id),
            "role": user.role.value,
            "org_id": str(user.organization_id) if user.organization_id else None,
            "branch_id": str(user.branch_id) if user.branch_id else None,
        })
        return {"Authorization": f"Bearer {token}"}
    return _headers


def test_superadmin_create_organization(client, db_session, auth_headers):
    """SuperAdmin can create a new organization."""
    super_admin = User(
        full_name="Super Admin",
        email=f"sa_{uuid.uuid4().hex[:6]}@chitties.io",
        phone="+919800000001",
        password_hash="pw",
        role=UserRole.SUPER_ADMIN,
    )
    db_session.add(super_admin)
    db_session.commit()

    reg_num = f"REG-TEST-{uuid.uuid4().hex[:6]}"
    payload = {
        "name": "Malabar Chits Ltd",
        "registration_number": reg_num,
        "tax_id": "32AABCC9999F1Z1",
        "state_registration_details": "Govt of Kerala Reg 2026",
    }

    response = client.post(
        "/api/v1/organizations",
        json=payload,
        headers=auth_headers(super_admin),
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Malabar Chits Ltd"
    assert data["registration_number"] == reg_num


def test_non_superadmin_cannot_create_organization(client, db_session, auth_headers):
    """Org Admin and Subscribers are barred from creating organizations (HTTP 403)."""
    org = Organization(name="Test Org", registration_number=f"REG-{uuid.uuid4().hex[:6]}")
    db_session.add(org)
    db_session.commit()

    org_admin = User(
        organization_id=org.id,
        full_name="Org Admin",
        email=f"oa_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919800000002",
        password_hash="pw",
        role=UserRole.ORG_ADMIN,
    )
    db_session.add(org_admin)
    db_session.commit()

    response = client.post(
        "/api/v1/organizations",
        json={"name": "Rogue Org", "registration_number": "ROGUE-01"},
        headers=auth_headers(org_admin),
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_list_organizations_paginated(client, db_session, auth_headers):
    """SuperAdmin lists organizations with pagination."""
    super_admin = User(
        full_name="Super Admin 2",
        email=f"sa2_{uuid.uuid4().hex[:6]}@chitties.io",
        phone="+919800000003",
        password_hash="pw",
        role=UserRole.SUPER_ADMIN,
    )
    db_session.add(super_admin)
    db_session.commit()

    response = client.get(
        "/api/v1/organizations?page=1&size=2",
        headers=auth_headers(super_admin),
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "items" in data
    assert "total_items" in data
    assert data["page"] == 1


def test_create_branch_and_uniqueness(client, db_session, auth_headers):
    """Org Admin creates a branch, and duplicate branch_code is rejected."""
    org = Organization(name="Branch Test Org", registration_number=f"REG-BTO-{uuid.uuid4().hex[:6]}")
    db_session.add(org)
    db_session.commit()

    admin = User(
        organization_id=org.id,
        full_name="Branch Creator",
        email=f"bc_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919800000004",
        password_hash="pw",
        role=UserRole.ORG_ADMIN,
    )
    db_session.add(admin)
    db_session.commit()

    payload = {
        "branch_code": "TNR-01",
        "name": "T Nagar Branch",
        "address": "Usman Road, Chennai",
        "phone": "044-24345678",
    }

    # 1. Successful creation
    r1 = client.post("/api/v1/branches", json=payload, headers=auth_headers(admin))
    assert r1.status_code == status.HTTP_201_CREATED
    assert r1.json()["branch_code"] == "TNR-01"

    # 2. Duplicate branch_code in same org -> 400 Bad Request
    r2 = client.post("/api/v1/branches", json=payload, headers=auth_headers(admin))
    assert r2.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in r2.json()["detail"]


def test_list_branches_tenant_scoping(client, db_session, auth_headers):
    """Branches of Org A are not visible to Org B."""
    org_a = Organization(name="Org Alpha", registration_number=f"REG-A-{uuid.uuid4().hex[:6]}")
    org_b = Organization(name="Org Beta", registration_number=f"REG-B-{uuid.uuid4().hex[:6]}")
    db_session.add_all([org_a, org_b])
    db_session.commit()

    b_a = Branch(organization_id=org_a.id, branch_code="A-01", name="Alpha Branch")
    b_b = Branch(organization_id=org_b.id, branch_code="B-01", name="Beta Branch")
    admin_a = User(
        organization_id=org_a.id,
        full_name="Admin Alpha",
        email=f"alpha_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919800000005",
        password_hash="pw",
        role=UserRole.ORG_ADMIN,
    )
    db_session.add_all([b_a, b_b, admin_a])
    db_session.commit()

    response = client.get("/api/v1/branches", headers=auth_headers(admin_a))
    assert response.status_code == status.HTTP_200_OK
    items = response.json()["items"]
    # Only Org Alpha's branches should be in the list
    assert all(item["organization_id"] == str(org_a.id) for item in items)


def test_onboard_member_and_kyc_workflow(client, db_session, auth_headers):
    """
    Test end-to-end member management:
    1. Branch Manager onboards new subscriber.
    2. Subscriber submits KYC document details.
    3. Unauthorized staff (Collection Agent) fails to approve KYC (HTTP 403).
    4. Branch Manager approves KYC -> transitions to VERIFIED.
    """
    org = Organization(name="Member Test Org", registration_number=f"REG-MTO-{uuid.uuid4().hex[:6]}")
    db_session.add(org)
    db_session.commit()

    branch = Branch(organization_id=org.id, branch_code="MB-01", name="Member Branch")
    db_session.add(branch)
    db_session.commit()

    bm = User(
        organization_id=org.id,
        branch_id=branch.id,
        full_name="Branch Manager Mark",
        email=f"mark_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919800000006",
        password_hash="pw",
        role=UserRole.BRANCH_MANAGER,
    )
    agent = User(
        organization_id=org.id,
        branch_id=branch.id,
        full_name="Field Agent Frank",
        email=f"frank_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919800000007",
        password_hash="pw",
        role=UserRole.COLLECTION_AGENT,
    )
    db_session.add_all([bm, agent])
    db_session.commit()

    # Step 1: Branch Manager onboards a new subscriber
    sub_email = f"subscriber_{uuid.uuid4().hex[:6]}@example.com"
    onboard_payload = {
        "full_name": "Daisy Subscriber",
        "email": sub_email,
        "phone": "+919800000008",
        "password": "Password123!",
        "role": "SUBSCRIBER",
        "branch_id": str(branch.id),
    }
    r_onboard = client.post("/api/v1/members", json=onboard_payload, headers=auth_headers(bm))
    assert r_onboard.status_code == status.HTTP_201_CREATED
    sub_id = r_onboard.json()["id"]
    assert r_onboard.json()["kyc_status"] == "PENDING"

    # Step 2: Subscriber submits KYC documents
    subscriber_user = db_session.query(User).filter(User.id == sub_id).first()
    kyc_payload = {
        "kyc_document_type": "AADHAAR",
        "kyc_document_number": "1234-5678-9012",
    }
    r_kyc = client.post(
        f"/api/v1/members/{sub_id}/kyc",
        json=kyc_payload,
        headers=auth_headers(subscriber_user),
    )
    assert r_kyc.status_code == status.HTTP_200_OK
    assert r_kyc.json()["kyc_document_type"] == "AADHAAR"

    # Step 3: Collection Agent tries to approve KYC -> 403 Forbidden
    r_agent_approve = client.patch(
        f"/api/v1/members/{sub_id}/kyc-status",
        json={"status": "VERIFIED"},
        headers=auth_headers(agent),
    )
    assert r_agent_approve.status_code == status.HTTP_403_FORBIDDEN

    # Step 4: Branch Manager approves KYC -> 200 OK, status VERIFIED
    r_bm_approve = client.patch(
        f"/api/v1/members/{sub_id}/kyc-status",
        json={"status": "VERIFIED"},
        headers=auth_headers(bm),
    )
    assert r_bm_approve.status_code == status.HTTP_200_OK
    assert r_bm_approve.json()["kyc_status"] == "VERIFIED"


def test_cross_tenant_member_access_blocked(client, db_session, auth_headers):
    """Staff from Org A cannot access or approve KYC for a member in Org B."""
    org_a = Organization(name="Company A", registration_number=f"REG-CA-{uuid.uuid4().hex[:6]}")
    org_b = Organization(name="Company B", registration_number=f"REG-CB-{uuid.uuid4().hex[:6]}")
    db_session.add_all([org_a, org_b])
    db_session.commit()

    manager_a = User(
        organization_id=org_a.id,
        full_name="Manager A",
        email=f"mgr_a_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919800000009",
        password_hash="pw",
        role=UserRole.BRANCH_MANAGER,
    )
    sub_b = User(
        organization_id=org_b.id,
        full_name="Subscriber B",
        email=f"sub_b_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919800000010",
        password_hash="pw",
        role=UserRole.SUBSCRIBER,
        kyc_status=KYCStatus.PENDING,
    )
    db_session.add_all([manager_a, sub_b])
    db_session.commit()

    # Manager A attempts to view Member B's details -> 403 Forbidden
    r_view = client.get(f"/api/v1/members/{sub_b.id}", headers=auth_headers(manager_a))
    assert r_view.status_code == status.HTTP_403_FORBIDDEN

    # Manager A attempts to approve Member B's KYC -> 403 Forbidden
    r_update = client.patch(
        f"/api/v1/members/{sub_b.id}/kyc-status",
        json={"status": "VERIFIED"},
        headers=auth_headers(manager_a),
    )
    assert r_update.status_code == status.HTTP_403_FORBIDDEN
