import uuid
from datetime import date, time
from decimal import Decimal
import pytest
from fastapi import status

from app.core.security import get_password_hash, create_access_token
from app.models.organization import Organization, Branch
from app.models.chit_scheme import ChitScheme
from app.models.chit_group import ChitGroup, ChitGroupStatus
from app.models.membership import ChitMembership, MembershipStatus
from app.models.installment import Installment
from app.models.auction import Auction
from app.models.user import User, UserRole, KYCStatus


@pytest.fixture
def auth_headers():
    def _headers(user: User):
        token = create_access_token({
            "sub": str(user.id),
            "role": user.role.value,
            "org_id": str(user.organization_id) if user.organization_id else None,
            "branch_id": str(user.branch_id) if user.branch_id else None,
        })
        return {"Authorization": f"Bearer {token}"}
    return _headers


def test_create_chit_scheme_and_scoping(client, db_session, auth_headers):
    """Org Admin creates a scheme template."""
    org = Organization(name="Scheme Org", registration_number=f"REG-SO-{uuid.uuid4().hex[:6]}")
    db_session.add(org)
    db_session.commit()

    admin = User(
        organization_id=org.id,
        full_name="Scheme Admin",
        email=f"admin_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919700000001",
        password_hash="pw",
        role=UserRole.ORG_ADMIN,
    )
    db_session.add(admin)
    db_session.commit()

    payload = {
        "name": "Gold 50K 5M",
        "total_value": 50000.00,
        "duration_months": 5,
        "monthly_installment": 10000.00,
        "foreman_commission_pct": 5.00,
        "max_bid_discount_pct": 30.00,
        "min_bid_discount_pct": 5.00,
        "foreman_month_one_reserved": True,
    }
    response = client.post("/api/v1/schemes", json=payload, headers=auth_headers(admin))
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Gold 50K 5M"
    assert Decimal(str(data["total_value"])) == Decimal("50000.00")
    assert data["duration_months"] == 5


def test_create_chit_group_and_uniqueness(client, db_session, auth_headers):
    """Org Admin creates a group from a scheme; duplicate group_code rejected."""
    org = Organization(name="Group Org", registration_number=f"REG-GO-{uuid.uuid4().hex[:6]}")
    db_session.add(org)
    db_session.commit()

    branch = Branch(organization_id=org.id, branch_code="GB-01", name="Group Branch")
    scheme = ChitScheme(
        organization_id=org.id,
        name="Test Scheme",
        total_value=Decimal("50000.00"),
        duration_months=5,
        monthly_installment=Decimal("10000.00"),
    )
    admin = User(
        organization_id=org.id,
        full_name="Group Admin",
        email=f"gadmin_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919700000002",
        password_hash="pw",
        role=UserRole.ORG_ADMIN,
    )
    db_session.add_all([branch, scheme, admin])
    db_session.commit()

    payload = {
        "scheme_id": str(scheme.id),
        "branch_id": str(branch.id),
        "group_code": "GRP-TEST-01",
        "start_date": "2026-03-01",
        "end_date": "2026-07-01",
        "auction_day_of_month": 15,
        "auction_time": "17:00:00",
    }
    # 1. Success
    r1 = client.post("/api/v1/groups", json=payload, headers=auth_headers(admin))
    assert r1.status_code == status.HTTP_201_CREATED
    assert r1.json()["group_code"] == "GRP-TEST-01"
    assert r1.json()["status"] == "DRAFT"

    # 2. Duplicate group_code -> 400 Bad Request
    r2 = client.post("/api/v1/groups", json=payload, headers=auth_headers(admin))
    assert r2.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in r2.json()["detail"]


def test_enrollment_kyc_and_ticket_rules(client, db_session, auth_headers):
    """
    Test strict ticket enrollment:
    1. Unverified KYC member cannot be enrolled.
    2. Verified member successfully enrolled to Ticket 1.
    3. Same member cannot take Ticket 2 (single ticket per user rule).
    4. Another member cannot take Ticket 1 (duplicate ticket rule).
    5. Ticket number > duration_months rejected (out of bounds).
    """
    org = Organization(name="Enroll Org", registration_number=f"REG-EO-{uuid.uuid4().hex[:6]}")
    db_session.add(org)
    db_session.commit()

    branch = Branch(organization_id=org.id, branch_code="EB-01", name="Enroll Branch")
    scheme = ChitScheme(
        organization_id=org.id,
        name="Small Scheme 3M",
        total_value=Decimal("30000.00"),
        duration_months=3,
        monthly_installment=Decimal("10000.00"),
    )
    admin = User(
        organization_id=org.id,
        branch_id=branch.id,
        full_name="Enroll Admin",
        email=f"eadmin_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919700000003",
        password_hash="pw",
        role=UserRole.ORG_ADMIN,
    )
    unverified_sub = User(
        organization_id=org.id,
        full_name="Unverified Sub",
        email=f"unver_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919700000004",
        password_hash="pw",
        role=UserRole.SUBSCRIBER,
        kyc_status=KYCStatus.PENDING,
    )
    verified_sub1 = User(
        organization_id=org.id,
        full_name="Verified Sub 1",
        email=f"vsub1_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919700000005",
        password_hash="pw",
        role=UserRole.SUBSCRIBER,
        kyc_status=KYCStatus.VERIFIED,
    )
    verified_sub2 = User(
        organization_id=org.id,
        full_name="Verified Sub 2",
        email=f"vsub2_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919700000006",
        password_hash="pw",
        role=UserRole.SUBSCRIBER,
        kyc_status=KYCStatus.VERIFIED,
    )
    db_session.add_all([branch, scheme, admin, unverified_sub, verified_sub1, verified_sub2])
    db_session.flush()

    group = ChitGroup(
        organization_id=org.id,
        branch_id=branch.id,
        scheme_id=scheme.id,
        group_code="GRP-ENROLL-01",
        start_date=date(2026, 3, 1),
        end_date=date(2026, 6, 1),
        auction_day_of_month=15,
        auction_time=time(17, 0),
        status=ChitGroupStatus.ENROLLING,
    )
    db_session.add(group)
    db_session.commit()

    # Rule 1: Unverified KYC subscriber rejected
    r_unver = client.post(
        f"/api/v1/groups/{group.id}/enroll",
        json={"user_id": str(unverified_sub.id), "ticket_number": 1},
        headers=auth_headers(admin),
    )
    assert r_unver.status_code == status.HTTP_400_BAD_REQUEST
    assert "Only VERIFIED subscribers" in r_unver.json()["detail"]

    # Rule 2: Verified member enrolled to Ticket 1
    r_v1 = client.post(
        f"/api/v1/groups/{group.id}/enroll",
        json={"user_id": str(verified_sub1.id), "ticket_number": 1},
        headers=auth_headers(admin),
    )
    assert r_v1.status_code == status.HTTP_201_CREATED
    assert r_v1.json()["ticket_number"] == 1

    # Rule 3: Same member takes Ticket 2 -> Rejected (Strictly 1 ticket per user)
    r_v1_second = client.post(
        f"/api/v1/groups/{group.id}/enroll",
        json={"user_id": str(verified_sub1.id), "ticket_number": 2},
        headers=auth_headers(admin),
    )
    assert r_v1_second.status_code == status.HTTP_400_BAD_REQUEST
    assert "Multiple tickets are prohibited" in r_v1_second.json()["detail"]

    # Rule 4: Sub 2 takes Ticket 1 -> Rejected (Ticket already allocated)
    r_v2_dup_ticket = client.post(
        f"/api/v1/groups/{group.id}/enroll",
        json={"user_id": str(verified_sub2.id), "ticket_number": 1},
        headers=auth_headers(admin),
    )
    assert r_v2_dup_ticket.status_code == status.HTTP_400_BAD_REQUEST
    assert "already been allocated" in r_v2_dup_ticket.json()["detail"]

    # Rule 5: Ticket number 4 in a 3-month scheme -> Out of bounds
    r_oob = client.post(
        f"/api/v1/groups/{group.id}/enroll",
        json={"user_id": str(verified_sub2.id), "ticket_number": 4},
        headers=auth_headers(admin),
    )
    assert r_oob.status_code == status.HTTP_400_BAD_REQUEST
    assert "between 1 and 3" in r_oob.json()["detail"]


def test_group_lifecycle_and_installment_generation(client, db_session, auth_headers):
    """
    Test group activation invariant:
    1. Incomplete capacity -> Activation rejected.
    2. 100% capacity filled -> Activation succeeds.
    3. Exactly N Installments generated for Month 1.
    4. Month 1 Auction record scheduled.
    """
    org = Organization(name="Lifecycle Org", registration_number=f"REG-LCO-{uuid.uuid4().hex[:6]}")
    db_session.add(org)
    db_session.commit()

    branch = Branch(organization_id=org.id, branch_code="LC-01", name="Lifecycle Branch")
    scheme = ChitScheme(
        organization_id=org.id,
        name="Micro 2M",
        total_value=Decimal("20000.00"),
        duration_months=2,
        monthly_installment=Decimal("10000.00"),
    )
    admin = User(
        organization_id=org.id,
        branch_id=branch.id,
        full_name="LC Admin",
        email=f"lc_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919700000007",
        password_hash="pw",
        role=UserRole.ORG_ADMIN,
    )
    u1 = User(
        organization_id=org.id,
        full_name="User One",
        email=f"u1_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919700000008",
        password_hash="pw",
        role=UserRole.SUBSCRIBER,
        kyc_status=KYCStatus.VERIFIED,
    )
    u2 = User(
        organization_id=org.id,
        full_name="User Two",
        email=f"u2_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919700000009",
        password_hash="pw",
        role=UserRole.SUBSCRIBER,
        kyc_status=KYCStatus.VERIFIED,
    )
    db_session.add_all([branch, scheme, admin, u1, u2])
    db_session.flush()

    group = ChitGroup(
        organization_id=org.id,
        branch_id=branch.id,
        scheme_id=scheme.id,
        group_code="GRP-ACTIVATE-01",
        start_date=date(2026, 4, 1),
        end_date=date(2026, 6, 1),
        auction_day_of_month=15,
        auction_time=time(17, 0),
        status=ChitGroupStatus.ENROLLING,
    )
    db_session.add(group)
    db_session.commit()

    # Step 1: Enroll only 1 out of 2 tickets
    client.post(
        f"/api/v1/groups/{group.id}/enroll",
        json={"user_id": str(u1.id), "ticket_number": 1},
        headers=auth_headers(admin),
    )

    # Attempt to activate with 1/2 tickets -> Rejected
    r_act_fail = client.patch(
        f"/api/v1/groups/{group.id}/status",
        json={"status": "ACTIVE"},
        headers=auth_headers(admin),
    )
    assert r_act_fail.status_code == status.HTTP_400_BAD_REQUEST
    assert "Incomplete enrollment" in r_act_fail.json()["detail"]

    # Step 2: Enroll ticket 2 (Now 2/2 tickets allocated)
    client.post(
        f"/api/v1/groups/{group.id}/enroll",
        json={"user_id": str(u2.id), "ticket_number": 2},
        headers=auth_headers(admin),
    )

    # Step 3: Activate group -> Succeeds!
    r_act_success = client.patch(
        f"/api/v1/groups/{group.id}/status",
        json={"status": "ACTIVE"},
        headers=auth_headers(admin),
    )
    assert r_act_success.status_code == status.HTTP_200_OK
    assert r_act_success.json()["status"] == "ACTIVE"

    # Step 4: Verify Month 1 Installments were generated for both tickets
    installments = db_session.query(Installment).filter(Installment.chit_group_id == group.id).all()
    assert len(installments) == 2
    for inst in installments:
        assert inst.month_number == 1
        assert inst.gross_amount == Decimal("10000.00")
        assert inst.net_due_amount == Decimal("10000.00")
        assert inst.status.value == "UNPAID"

    # Step 5: Verify Month 1 Auction was scheduled
    auction = db_session.query(Auction).filter(Auction.chit_group_id == group.id).first()
    assert auction is not None
    assert auction.month_number == 1
    assert auction.status.value == "SCHEDULED"
