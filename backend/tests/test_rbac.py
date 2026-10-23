import uuid
from datetime import date, time, datetime, timezone
from decimal import Decimal
import pytest
from fastapi import status

from app.core.security import get_password_hash, create_access_token
from app.models.organization import Organization, Branch
from app.models.chit_scheme import ChitScheme
from app.models.chit_group import ChitGroup, ChitGroupStatus
from app.models.membership import ChitMembership, MembershipStatus
from app.models.installment import Installment, InstallmentStatus
from app.models.auction import Auction, AuctionStatus
from app.models.payout import Payout, PayoutStatus, Surety, SuretyStatus, SuretyType
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


@pytest.fixture
def rbac_fixture(db_session):
    """
    Sets up a comprehensive multi-role environment:
    - 2 Organizations (Org A and Org B) for tenant isolation
    - In Org A:
      - admin_a (ADMIN)
      - mgr_assigned (MANAGER) - assigned to group_a1
      - mgr_unassigned (MANAGER) - NOT assigned to group_a1 (assigned to group_a2)
      - accountant_a (ACCOUNTANT)
      - member_1 (MEMBER) - holds Ticket 1 in group_a1
      - member_2 (MEMBER) - holds Ticket 2 in group_a1
    - In Org B:
      - admin_b (ADMIN)
      - member_b (MEMBER)
    """
    # Org A
    org_a = Organization(name="Apex Chits A", registration_number=f"REG-A-{uuid.uuid4().hex[:6]}")
    org_b = Organization(name="Zenith Chits B", registration_number=f"REG-B-{uuid.uuid4().hex[:6]}")
    db_session.add_all([org_a, org_b])
    db_session.commit()

    branch_a = Branch(organization_id=org_a.id, name="Branch A", branch_code=f"BA-{uuid.uuid4().hex[:4]}")
    branch_b = Branch(organization_id=org_b.id, name="Branch B", branch_code=f"BB-{uuid.uuid4().hex[:4]}")
    db_session.add_all([branch_a, branch_b])
    db_session.commit()

    # Users in Org A
    admin_a = User(
        organization_id=org_a.id,
        branch_id=branch_a.id,
        full_name="Admin Alice",
        email=f"admin_a_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919900110001",
        password_hash=get_password_hash("password123"),
        role=UserRole.ADMIN,
        kyc_status=KYCStatus.VERIFIED,
    )
    mgr_assigned = User(
        organization_id=org_a.id,
        branch_id=branch_a.id,
        full_name="Manager Bob",
        email=f"mgr_assigned_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919900110002",
        password_hash=get_password_hash("password123"),
        role=UserRole.MANAGER,
        kyc_status=KYCStatus.VERIFIED,
    )
    mgr_unassigned = User(
        organization_id=org_a.id,
        branch_id=branch_a.id,
        full_name="Manager Charlie",
        email=f"mgr_unassigned_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919900110003",
        password_hash=get_password_hash("password123"),
        role=UserRole.MANAGER,
        kyc_status=KYCStatus.VERIFIED,
    )
    accountant_a = User(
        organization_id=org_a.id,
        branch_id=branch_a.id,
        full_name="Accountant Dave",
        email=f"acct_a_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919900110004",
        password_hash=get_password_hash("password123"),
        role=UserRole.ACCOUNTANT,
        kyc_status=KYCStatus.VERIFIED,
    )
    member_1 = User(
        organization_id=org_a.id,
        branch_id=branch_a.id,
        full_name="Member One",
        email=f"mem1_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919900110005",
        password_hash=get_password_hash("password123"),
        role=UserRole.MEMBER,
        kyc_status=KYCStatus.VERIFIED,
    )
    member_2 = User(
        organization_id=org_a.id,
        branch_id=branch_a.id,
        full_name="Member Two",
        email=f"mem2_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919900110006",
        password_hash=get_password_hash("password123"),
        role=UserRole.MEMBER,
        kyc_status=KYCStatus.VERIFIED,
    )

    # Users in Org B
    admin_b = User(
        organization_id=org_b.id,
        branch_id=branch_b.id,
        full_name="Admin Brenda",
        email=f"admin_b_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919900110007",
        password_hash=get_password_hash("password123"),
        role=UserRole.ADMIN,
        kyc_status=KYCStatus.VERIFIED,
    )
    member_b = User(
        organization_id=org_b.id,
        branch_id=branch_b.id,
        full_name="Member Beta",
        email=f"memb_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919900110008",
        password_hash=get_password_hash("password123"),
        role=UserRole.MEMBER,
        kyc_status=KYCStatus.VERIFIED,
    )

    db_session.add_all([admin_a, mgr_assigned, mgr_unassigned, accountant_a, member_1, member_2, admin_b, member_b])
    db_session.commit()

    # Scheme
    scheme = ChitScheme(
        organization_id=org_a.id,
        name="Apex 50K 5M",
        total_value=Decimal("50000.00"),
        duration_months=5,
        monthly_installment=Decimal("10000.00"),
        foreman_commission_pct=Decimal("5.00"),
        min_bid_discount_pct=Decimal("5.00"),
        max_bid_discount_pct=Decimal("30.00"),
        is_active=True,
    )
    db_session.add(scheme)
    db_session.commit()

    # Group 1 (Assigned to mgr_assigned)
    group_1 = ChitGroup(
        organization_id=org_a.id,
        branch_id=branch_a.id,
        scheme_id=scheme.id,
        manager_id=mgr_assigned.id,
        group_code="GRP-A1",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 10, 31),
        current_month=1,
        auction_day_of_month=15,
        auction_time=time(16, 0),
        status=ChitGroupStatus.ACTIVE,
    )
    # Group 2 (Assigned to mgr_unassigned)
    group_2 = ChitGroup(
        organization_id=org_a.id,
        branch_id=branch_a.id,
        scheme_id=scheme.id,
        manager_id=mgr_unassigned.id,
        group_code="GRP-A2",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 10, 31),
        current_month=1,
        auction_day_of_month=15,
        auction_time=time(16, 0),
        status=ChitGroupStatus.ACTIVE,
    )
    db_session.add_all([group_1, group_2])
    db_session.commit()

    # Memberships in Group 1
    mem1 = ChitMembership(
        chit_group_id=group_1.id,
        user_id=member_1.id,
        ticket_number=1,
        status=MembershipStatus.ACTIVE,
    )
    mem2 = ChitMembership(
        chit_group_id=group_1.id,
        user_id=member_2.id,
        ticket_number=2,
        status=MembershipStatus.ACTIVE,
    )
    db_session.add_all([mem1, mem2])
    db_session.commit()

    # Installment dues Month 1
    inst1 = Installment(
        chit_group_id=group_1.id,
        chit_membership_id=mem1.id,
        month_number=1,
        due_date=date(2026, 6, 10),
        gross_amount=Decimal("10000.00"),
        dividend_amount=Decimal("0.00"),
        penalty_amount=Decimal("0.00"),
        net_due_amount=Decimal("10000.00"),
        paid_amount=Decimal("0.00"),
        status=InstallmentStatus.UNPAID,
    )
    inst2 = Installment(
        chit_group_id=group_1.id,
        chit_membership_id=mem2.id,
        month_number=1,
        due_date=date(2026, 6, 10),
        gross_amount=Decimal("10000.00"),
        dividend_amount=Decimal("0.00"),
        penalty_amount=Decimal("0.00"),
        net_due_amount=Decimal("10000.00"),
        paid_amount=Decimal("0.00"),
        status=InstallmentStatus.UNPAID,
    )
    db_session.add_all([inst1, inst2])

    # Auction Month 1 for Group 1
    auction_1 = Auction(
        chit_group_id=group_1.id,
        month_number=1,
        scheduled_at=datetime.now(timezone.utc),
        status=AuctionStatus.SCHEDULED,
    )
    db_session.add(auction_1)
    db_session.commit()

    return {
        "org_a": org_a,
        "org_b": org_b,
        "branch_a": branch_a,
        "admin_a": admin_a,
        "mgr_assigned": mgr_assigned,
        "mgr_unassigned": mgr_unassigned,
        "accountant_a": accountant_a,
        "member_1": member_1,
        "member_2": member_2,
        "admin_b": admin_b,
        "member_b": member_b,
        "group_1": group_1,
        "group_2": group_2,
        "mem1": mem1,
        "mem2": mem2,
        "inst1": inst1,
        "inst2": inst2,
        "auction_1": auction_1,
        "scheme": scheme,
    }


# ==============================================================================
# 1. Unauthenticated Requests
# ==============================================================================
def test_unauthenticated_requests_fail(client, rbac_fixture):
    """Endpoints reject requests lacking authentication token with 401."""
    f = rbac_fixture
    assert client.get("/api/v1/groups").status_code == status.HTTP_401_UNAUTHORIZED
    assert client.get("/api/v1/members").status_code == status.HTTP_401_UNAUTHORIZED
    assert client.get("/api/v1/payouts").status_code == status.HTTP_401_UNAUTHORIZED
    assert client.get("/api/v1/audit-logs").status_code == status.HTTP_401_UNAUTHORIZED
    assert client.get(f"/api/v1/groups/{f['group_1'].id}").status_code == status.HTTP_401_UNAUTHORIZED
    assert client.get("/api/v1/payments").status_code == status.HTTP_404_NOT_FOUND


# ==============================================================================
# 2. Admin Capabilities & Restrictions
# ==============================================================================
def test_admin_full_access_and_audit_logs(client, rbac_fixture, auth_headers):
    """Admin can view groups, configure groups, assign managers, and view audit logs."""
    f = rbac_fixture
    h_admin = auth_headers(f["admin_a"])

    # Admin can list all groups in Org A
    r_groups = client.get("/api/v1/groups", headers=h_admin)
    assert r_groups.status_code == status.HTTP_200_OK
    assert len(r_groups.json()["items"]) >= 2

    # Admin can assign manager to group
    r_assign = client.post(
        f"/api/v1/groups/{f['group_1'].id}/assign-manager",
        json={"manager_id": str(f["mgr_unassigned"].id)},
        headers=h_admin,
    )
    assert r_assign.status_code == status.HTTP_200_OK
    assert r_assign.json()["manager_id"] == str(f["mgr_unassigned"].id)

    # Re-assign back to mgr_assigned
    client.post(
        f"/api/v1/groups/{f['group_1'].id}/assign-manager",
        json={"manager_id": str(f["mgr_assigned"].id)},
        headers=h_admin,
    )

    # Admin can view audit logs
    r_audit = client.get("/api/v1/audit-logs", headers=h_admin)
    assert r_audit.status_code == status.HTTP_200_OK


def test_admin_cross_tenant_isolation(client, rbac_fixture, auth_headers):
    """Admin from Org B cannot access groups or members belonging to Org A."""
    f = rbac_fixture
    h_admin_b = auth_headers(f["admin_b"])

    # Admin B accessing Org A's group -> 404 Not Found
    r_group = client.get(f"/api/v1/groups/{f['group_1'].id}", headers=h_admin_b)
    assert r_group.status_code == status.HTTP_404_NOT_FOUND

    # Admin B accessing Org A's member -> 403 Forbidden (cross-tenant)
    r_member = client.get(f"/api/v1/members/{f['member_1'].id}", headers=h_admin_b)
    assert r_member.status_code == status.HTTP_403_FORBIDDEN


# ==============================================================================
# 3. Manager Scope & Strict Prohibitions
# ==============================================================================
def test_manager_scoped_to_assigned_groups(client, rbac_fixture, auth_headers):
    """Manager can only view assigned groups; unassigned groups return 404."""
    f = rbac_fixture
    h_assigned = auth_headers(f["mgr_assigned"])
    h_unassigned = auth_headers(f["mgr_unassigned"])

    # Assigned manager can access Group 1
    r_ok = client.get(f"/api/v1/groups/{f['group_1'].id}", headers=h_assigned)
    assert r_ok.status_code == status.HTTP_200_OK

    # Unassigned manager accessing Group 1 -> 404 Not Found
    r_blocked = client.get(f"/api/v1/groups/{f['group_1'].id}", headers=h_unassigned)
    assert r_blocked.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.skip(reason="Payments module temporarily deferred; endpoints deactivated")
def test_manager_forbidden_from_recording_payments(client, rbac_fixture, auth_headers):
    """Manager is strictly prohibited from recording payments (HTTP 403)."""
    f = rbac_fixture
    h_mgr = auth_headers(f["mgr_assigned"])

    payload = {
        "installment_id": str(f["inst1"].id),
        "amount": 10000.00,
        "payment_method": "CASH",
        "notes": "Manager attempt to collect cash directly",
    }
    resp = client.post("/api/v1/payments", json=payload, headers=h_mgr)
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    assert "RECORD_PAYMENTS" in resp.json()["detail"] or "restricted" in resp.json()["detail"]


def test_manager_cannot_create_groups_or_assign_roles(client, rbac_fixture, auth_headers):
    """Manager cannot create groups, assign managers, or onboard staff with admin/manager roles."""
    f = rbac_fixture
    h_mgr = auth_headers(f["mgr_assigned"])

    # Manager creating group -> 403 Forbidden
    group_payload = {
        "scheme_id": str(f["scheme"].id),
        "branch_id": str(f["branch_a"].id),
        "group_code": "ROGUE-GRP",
        "start_date": "2026-07-01",
        "end_date": "2026-11-30",
        "auction_day_of_month": 15,
        "auction_time": "16:00:00",
    }
    assert client.post("/api/v1/groups", json=group_payload, headers=h_mgr).status_code == status.HTTP_403_FORBIDDEN

    # Manager assigning manager -> 403 Forbidden
    assign_payload = {"manager_id": str(f["mgr_assigned"].id)}
    assert client.post(f"/api/v1/groups/{f['group_1'].id}/assign-manager", json=assign_payload, headers=h_mgr).status_code == status.HTTP_403_FORBIDDEN

    # Manager onboarding another ADMIN -> 403 Forbidden
    admin_onboard = {
        "full_name": "Rogue Admin",
        "email": f"rogue_{uuid.uuid4().hex[:6]}@example.com",
        "phone": "+919900990099",
        "password": "Password123!",
        "role": "ADMIN",
        "branch_id": str(f["branch_a"].id),
    }
    r_bad_role = client.post("/api/v1/members", json=admin_onboard, headers=h_mgr)
    assert r_bad_role.status_code == status.HTTP_403_FORBIDDEN


def test_manager_cannot_view_audit_logs(client, rbac_fixture, auth_headers):
    """Manager is barred from viewing system audit logs (HTTP 403)."""
    f = rbac_fixture
    assert client.get("/api/v1/audit-logs", headers=auth_headers(f["mgr_assigned"])).status_code == status.HTTP_403_FORBIDDEN


# ==============================================================================
# 4. Accountant Capabilities & Dual-Control Restrictions
# ==============================================================================
@pytest.mark.skip(reason="Payments module temporarily deferred; endpoints deactivated")
def test_accountant_can_record_payments_and_generate_receipts(client, rbac_fixture, auth_headers):
    """Accountant records installment collection and generates digital receipt."""
    f = rbac_fixture
    h_acct = auth_headers(f["accountant_a"])

    payload = {
        "installment_id": str(f["inst1"].id),
        "amount": 10000.00,
        "payment_method": "BANK_TRANSFER",
        "transaction_reference": f"NEFT-ACCT-{uuid.uuid4().hex[:8]}",
        "notes": "Bank transfer reconciled by accountant",
    }
    resp = client.post("/api/v1/payments", json=payload, headers=h_acct)
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert float(data["amount_paid"]) == 10000.00
    assert data["receipt_number"].startswith("REC-")


def test_accountant_cannot_modify_groups_or_users(client, rbac_fixture, auth_headers):
    """Accountant cannot create chit groups, onboard users, or view audit logs."""
    f = rbac_fixture
    h_acct = auth_headers(f["accountant_a"])

    # Cannot create group
    assert client.post("/api/v1/groups", json={}, headers=h_acct).status_code == status.HTTP_403_FORBIDDEN

    # Cannot onboard user
    assert client.post("/api/v1/members", json={}, headers=h_acct).status_code == status.HTTP_403_FORBIDDEN

    # Cannot view audit logs
    assert client.get("/api/v1/audit-logs", headers=h_acct).status_code == status.HTTP_403_FORBIDDEN


def test_accountant_payout_dual_control_restriction(client, db_session, rbac_fixture, auth_headers):
    """Accountant cannot independently disburse prize money without Admin dual-control approval."""
    f = rbac_fixture
    h_acct = auth_headers(f["accountant_a"])

    # Create concluded auction & payout claim in SURETY_APPROVED status
    auction = Auction(
        chit_group_id=f["group_1"].id,
        month_number=2,
        scheduled_at=datetime.now(timezone.utc),
        opened_at=datetime.now(timezone.utc),
        closed_at=datetime.now(timezone.utc),
        status=AuctionStatus.CLOSED,
        winning_membership_id=f["mem1"].id,
        winning_bid_discount=Decimal("10000.00"),
        foreman_commission=Decimal("2500.00"),
        total_dividend_pool=Decimal("7500.00"),
        dividend_per_ticket=Decimal("1500.00"),
        net_payable_installment=Decimal("8500.00"),
    )
    db_session.add(auction)
    db_session.flush()

    payout = Payout(
        auction_id=auction.id,
        chit_membership_id=f["mem1"].id,
        gross_prize_amount=Decimal("40000.00"),
        foreman_charges_deducted=Decimal("0.00"),
        arrears_deducted=Decimal("0.00"),
        net_disbursed_amount=Decimal("40000.00"),
        disbursement_status=PayoutStatus.SURETY_APPROVED,
    )
    db_session.add(payout)
    db_session.commit()

    # Accountant attempts disbursement -> Blocked under dual-control requirement (HTTP 403)
    disburse_payload = {
        "disbursement_reference": "NEFT-DUAL-001",
        "foreman_charges_deducted": 0.00,
        "auto_clear_arrears": False,
    }
    resp = client.post(f"/api/v1/payouts/{payout.id}/disburse", json=disburse_payload, headers=h_acct)
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    assert "Dual-control" in resp.json()["detail"] or "APPROVE_SENSITIVE_FINANCIAL_OPS" in resp.json()["detail"]


# ==============================================================================
# 5. Member (Subscriber) Scope & Restrictions
# ==============================================================================
def test_member_can_view_own_ticket_statement(client, rbac_fixture, auth_headers):
    """Member can view own statement ledger."""
    f = rbac_fixture
    h_sub1 = auth_headers(f["member_1"])

    # Member 1 views own ledger
    r_ledger = client.get(f"/api/v1/installments/membership/{f['mem1'].id}", headers=h_sub1)
    assert r_ledger.status_code == status.HTTP_200_OK


def test_member_cannot_view_other_members_records(client, rbac_fixture, auth_headers):
    """Member 1 is strictly forbidden from accessing Member 2's profile or ledger."""
    f = rbac_fixture
    h_sub1 = auth_headers(f["member_1"])

    # Member 1 accessing Member 2's profile -> 403 Forbidden
    r_profile = client.get(f"/api/v1/members/{f['member_2'].id}", headers=h_sub1)
    assert r_profile.status_code == status.HTTP_403_FORBIDDEN

    # Member 1 accessing Member 2's ledger -> 403 Forbidden
    r_ledger2 = client.get(f"/api/v1/installments/membership/{f['mem2'].id}", headers=h_sub1)
    assert r_ledger2.status_code == status.HTTP_403_FORBIDDEN


def test_member_cannot_access_staff_endpoints(client, rbac_fixture, auth_headers):
    """Member is barred from member directory, group creation, group dues, and audit logs."""
    f = rbac_fixture
    h_sub = auth_headers(f["member_1"])

    # Directory
    assert client.get("/api/v1/members", headers=h_sub).status_code == status.HTTP_403_FORBIDDEN

    # Group dues
    assert client.get(f"/api/v1/installments/group/{f['group_1'].id}", headers=h_sub).status_code == status.HTTP_403_FORBIDDEN

    # Create group
    assert client.post("/api/v1/groups", json={}, headers=h_sub).status_code == status.HTTP_403_FORBIDDEN

    # Start auction
    assert client.post(f"/api/v1/auctions/{f['auction_1'].id}/start", headers=h_sub).status_code == status.HTTP_403_FORBIDDEN

    # Audit logs
    assert client.get("/api/v1/audit-logs", headers=h_sub).status_code == status.HTTP_403_FORBIDDEN


# ==============================================================================
# 6. Branch Manager Surety Verification & Dual-Control Disbursement Check
# ==============================================================================
def test_branch_manager_can_verify_surety_but_cannot_disburse(client, db_session, rbac_fixture, auth_headers):
    """
    Branch Manager is authorized to inspect and verify sureties submitted by winning subscribers,
    but is strictly barred from authorizing final prize disbursement under dual control.
    """
    f = rbac_fixture
    h_mgr = auth_headers(f["mgr_assigned"])

    # Concluded auction in Group 1
    auction = Auction(
        chit_group_id=f["group_1"].id,
        month_number=3,
        scheduled_at=datetime.now(timezone.utc),
        opened_at=datetime.now(timezone.utc),
        closed_at=datetime.now(timezone.utc),
        status=AuctionStatus.CLOSED,
        winning_membership_id=f["mem1"].id,
        winning_bid_discount=Decimal("12000.00"),
        foreman_commission=Decimal("2500.00"),
        total_dividend_pool=Decimal("9500.00"),
        dividend_per_ticket=Decimal("1900.00"),
        net_payable_installment=Decimal("8100.00"),
    )
    db_session.add(auction)
    db_session.flush()

    payout = Payout(
        auction_id=auction.id,
        chit_membership_id=f["mem1"].id,
        gross_prize_amount=Decimal("38000.00"),
        foreman_charges_deducted=Decimal("0.00"),
        arrears_deducted=Decimal("0.00"),
        net_disbursed_amount=Decimal("38000.00"),
        disbursement_status=PayoutStatus.PENDING_SURETY,
    )
    db_session.add(payout)
    db_session.flush()

    surety = Surety(
        payout_id=payout.id,
        surety_type=SuretyType.GUARANTOR,
        guarantor_name="Surety Guarantor",
        guarantor_phone="+919876543999",
        document_reference="DOC-REF-001",
        verification_status=SuretyStatus.PENDING,
    )
    db_session.add(surety)
    db_session.commit()

    # 1. Branch Manager verifies surety -> HTTP 200 OK
    verify_payload = {
        "verification_status": "VERIFIED",
        "remarks": "Salary documents verified by Manager",
    }
    r_verify = client.patch(f"/api/v1/payouts/sureties/{surety.id}/verify", json=verify_payload, headers=h_mgr)
    assert r_verify.status_code == status.HTTP_200_OK
    assert r_verify.json()["verification_status"] == "VERIFIED"

    # 2. Branch Manager attempts final disbursement -> HTTP 403 Forbidden (Dual Control)
    disburse_payload = {
        "disbursement_reference": "MGR-THEFT-DISBURSE",
        "foreman_charges_deducted": 0.00,
        "auto_clear_arrears": True,
    }
    r_disburse = client.post(f"/api/v1/payouts/{payout.id}/disburse", json=disburse_payload, headers=h_mgr)
    assert r_disburse.status_code == status.HTTP_403_FORBIDDEN


# ==============================================================================
# 7. SuperAdmin vs OrgAdmin Explicit Scope Distinction
# ==============================================================================
def test_superadmin_vs_orgadmin_tenant_provisioning_scope(client, db_session, rbac_fixture, auth_headers):
    """
    SuperAdmin (organization_id is None) can list and provision tenants.
    OrgAdmin (bound to an organization) is forbidden from tenant-level provisioning.
    """
    f = rbac_fixture

    # SuperAdmin user without organization
    super_admin = User(
        organization_id=None,
        branch_id=None,
        full_name="Global SuperAdmin",
        email=f"global_super_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919900990001",
        password_hash=get_password_hash("password123"),
        role=UserRole.SUPER_ADMIN,
        kyc_status=KYCStatus.VERIFIED,
    )
    db_session.add(super_admin)
    db_session.commit()

    h_super = auth_headers(super_admin)
    h_org_admin = auth_headers(f["admin_a"])

    # SuperAdmin can list organizations
    r_list = client.get("/api/v1/organizations", headers=h_super)
    assert r_list.status_code == status.HTTP_200_OK

    # OrgAdmin listing all organizations -> 403 Forbidden
    r_blocked = client.get("/api/v1/organizations", headers=h_org_admin)
    assert r_blocked.status_code == status.HTTP_403_FORBIDDEN

