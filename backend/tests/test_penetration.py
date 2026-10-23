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
from app.models.auction import Auction, AuctionStatus, Bid
from app.models.payout import Payout, PayoutStatus, Surety, SuretyType, SuretyStatus
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


def setup_multi_tenant_environment(db_session):
    """Sets up two strictly separated tenants (Tenant Alpha and Tenant Beta)."""
    # Tenant Alpha
    org_a = Organization(name="Tenant Alpha", registration_number=f"REG-A-{uuid.uuid4().hex[:6]}")
    db_session.add(org_a)
    db_session.commit()

    branch_a = Branch(organization_id=org_a.id, name="Alpha Branch", branch_code=f"AB-{uuid.uuid4().hex[:4]}", address="City A")
    db_session.add(branch_a)
    db_session.commit()

    admin_a = User(
        organization_id=org_a.id,
        branch_id=branch_a.id,
        full_name="Admin Alpha",
        email=f"admin_a_{uuid.uuid4().hex[:6]}@alpha.com",
        phone="+919000000001",
        password_hash=get_password_hash("password123"),
        role=UserRole.ORG_ADMIN,
        kyc_status=KYCStatus.VERIFIED,
    )
    sub_a = User(
        organization_id=org_a.id,
        branch_id=branch_a.id,
        full_name="Subscriber Alpha",
        email=f"sub_a_{uuid.uuid4().hex[:6]}@alpha.com",
        phone="+919000000002",
        password_hash=get_password_hash("password123"),
        role=UserRole.SUBSCRIBER,
        kyc_status=KYCStatus.VERIFIED,
    )
    db_session.add_all([admin_a, sub_a])
    db_session.commit()

    # Tenant Beta
    org_b = Organization(name="Tenant Beta", registration_number=f"REG-B-{uuid.uuid4().hex[:6]}")
    db_session.add(org_b)
    db_session.commit()

    branch_b = Branch(organization_id=org_b.id, name="Beta Branch", branch_code=f"BB-{uuid.uuid4().hex[:4]}", address="City B")
    db_session.add(branch_b)
    db_session.commit()

    admin_b = User(
        organization_id=org_b.id,
        branch_id=branch_b.id,
        full_name="Admin Beta",
        email=f"admin_b_{uuid.uuid4().hex[:6]}@beta.com",
        phone="+919000000003",
        password_hash=get_password_hash("password123"),
        role=UserRole.ORG_ADMIN,
        kyc_status=KYCStatus.VERIFIED,
    )
    sub_b = User(
        organization_id=org_b.id,
        branch_id=branch_b.id,
        full_name="Subscriber Beta",
        email=f"sub_b_{uuid.uuid4().hex[:6]}@beta.com",
        phone="+919000000004",
        password_hash=get_password_hash("password123"),
        role=UserRole.SUBSCRIBER,
        kyc_status=KYCStatus.VERIFIED,
    )
    db_session.add_all([admin_b, sub_b])
    db_session.commit()

    # Schemes and Groups for Alpha
    scheme_a = ChitScheme(
        organization_id=org_a.id,
        name="Alpha 100K",
        total_value=Decimal("100000.00"),
        duration_months=5,
        monthly_installment=Decimal("20000.00"),
        foreman_commission_pct=Decimal("5.00"),
    )
    db_session.add(scheme_a)
    db_session.commit()

    group_a = ChitGroup(
        organization_id=org_a.id,
        branch_id=branch_a.id,
        scheme_id=scheme_a.id,
        group_code=f"ALPHA-G-{uuid.uuid4().hex[:4]}",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 1),
        current_month=1,
        auction_day_of_month=15,
        auction_time=time(15, 0),
        status=ChitGroupStatus.ACTIVE,
    )
    db_session.add(group_a)
    db_session.commit()

    ticket_a = ChitMembership(
        chit_group_id=group_a.id,
        user_id=sub_a.id,
        ticket_number=1,
        status=MembershipStatus.ACTIVE,
    )
    db_session.add(ticket_a)
    db_session.commit()

    # Schemes and Groups for Beta
    scheme_b = ChitScheme(
        organization_id=org_b.id,
        name="Beta 200K",
        total_value=Decimal("200000.00"),
        duration_months=10,
        monthly_installment=Decimal("20000.00"),
        foreman_commission_pct=Decimal("5.00"),
    )
    db_session.add(scheme_b)
    db_session.commit()

    group_b = ChitGroup(
        organization_id=org_b.id,
        branch_id=branch_b.id,
        scheme_id=scheme_b.id,
        group_code=f"BETA-G-{uuid.uuid4().hex[:4]}",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 11, 1),
        current_month=1,
        auction_day_of_month=20,
        auction_time=time(16, 0),
        status=ChitGroupStatus.ACTIVE,
    )
    db_session.add(group_b)
    db_session.commit()

    ticket_b = ChitMembership(
        chit_group_id=group_b.id,
        user_id=sub_b.id,
        ticket_number=1,
        status=MembershipStatus.ACTIVE,
    )
    db_session.add(ticket_b)
    db_session.commit()

    # Auction for Beta
    auction_b = Auction(
        chit_group_id=group_b.id,
        month_number=1,
        scheduled_at=datetime.now(timezone.utc),
        status=AuctionStatus.OPEN,
    )
    db_session.add(auction_b)
    db_session.commit()

    return {
        "org_a": org_a,
        "branch_a": branch_a,
        "admin_a": admin_a,
        "sub_a": sub_a,
        "scheme_a": scheme_a,
        "group_a": group_a,
        "ticket_a": ticket_a,
        "org_b": org_b,
        "branch_b": branch_b,
        "admin_b": admin_b,
        "sub_b": sub_b,
        "scheme_b": scheme_b,
        "group_b": group_b,
        "ticket_b": ticket_b,
        "auction_b": auction_b,
    }


def test_cross_tenant_member_idor_blocked(client, db_session, auth_headers):
    """Attack 1: Org A admin attempts to read or modify member KYC of Org B."""
    env = setup_multi_tenant_environment(db_session)
    hdr_a = auth_headers(env["admin_a"])

    # Attempt to read subscriber B's profile
    res = client.get(f"/api/v1/members/{env['sub_b'].id}", headers=hdr_a)
    assert res.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

    # Attempt to verify KYC of subscriber B using Admin A token
    res_kyc = client.patch(
        f"/api/v1/members/{env['sub_b'].id}/kyc-status",
        json={"status": "VERIFIED"},
        headers=hdr_a,
    )
    assert res_kyc.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)


def test_cross_tenant_branch_tampering_blocked(client, db_session, auth_headers):
    """Attack 2: Org A admin attempts to list or update branches of Org B."""
    env = setup_multi_tenant_environment(db_session)
    hdr_a = auth_headers(env["admin_a"])

    # Listing branches with admin A token should ONLY return Alpha branches
    res = client.get("/api/v1/branches", headers=hdr_a)
    assert res.status_code == status.HTTP_200_OK
    branch_ids = [b["id"] for b in res.json()["items"]]
    assert str(env["branch_b"].id) not in branch_ids
    assert str(env["branch_a"].id) in branch_ids


def test_cross_tenant_auction_bidding_blocked(client, db_session, auth_headers):
    """Attack 3: Subscriber from Tenant A attempts to bid in Tenant B's auction."""
    env = setup_multi_tenant_environment(db_session)
    hdr_sub_a = auth_headers(env["sub_a"])

    # Sub A attempts to place bid on Auction B
    bid_payload = {
        "bid_discount_amount": 10000.00,
    }
    res = client.post(
        f"/api/v1/auctions/{env['auction_b'].id}/bids",
        json=bid_payload,
        headers=hdr_sub_a,
    )
    assert res.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)


def test_cross_tenant_security_deposit_tampering_blocked(client, db_session, auth_headers):
    """Attack 4: Admin A attempts to pledge or access security deposit for Tenant B's circle."""
    env = setup_multi_tenant_environment(db_session)
    hdr_a = auth_headers(env["admin_a"])

    # Attempt to lodge deposit against Group B
    bad_deposit = {
        "group_id": str(env["group_b"].id),
        "deposit_type": "FIXED_DEPOSIT",
        "bank_name": "Canara Bank",
        "account_or_fdr_number": "FDR-MALICIOUS-01",
        "amount": 200000.00,
        "deposit_date": str(date(2026, 1, 1)),
        "maturity_date": str(date(2026, 12, 31)),
        "registrar_order_reference": "REF-CROSS-01",
    }
    res = client.post("/api/v1/compliance/deposits", json=bad_deposit, headers=hdr_a)
    assert res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.skip(reason="Payments module temporarily deferred; endpoints deactivated")
def test_payment_idempotency_token_collision_blocked(client, db_session, auth_headers):
    """Attack 5: Replaying identical transaction reference token across distinct payments."""
    env = setup_multi_tenant_environment(db_session)
    hdr_a = auth_headers(env["admin_a"])

    # Create month 1 installment for ticket A
    inst = Installment(
        chit_group_id=env["group_a"].id,
        chit_membership_id=env["ticket_a"].id,
        month_number=1,
        due_date=date(2026, 1, 15),
        gross_amount=Decimal("20000.00"),
        net_due_amount=Decimal("20000.00"),
        paid_amount=Decimal("0.00"),
        status=InstallmentStatus.UNPAID,
    )
    db_session.add(inst)
    db_session.commit()

    token = f"TOKEN-REPLAY-{uuid.uuid4().hex[:8]}"
    pay_payload = {
        "installment_id": str(inst.id),
        "amount": 10000.00,
        "payment_method": "UPI",
        "transaction_reference": token,
    }

    # First payment succeeds
    res1 = client.post("/api/v1/payments", json=pay_payload, headers=hdr_a)
    assert res1.status_code == status.HTTP_201_CREATED
    pay_id1 = res1.json()["id"]

    # Replay identical token by Tenant A -> Must return identical existing payment (Idempotency)
    res2 = client.post("/api/v1/payments", json=pay_payload, headers=hdr_a)
    assert res2.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED)
    assert res2.json()["id"] == pay_id1

    # Cross-Tenant Replay Attack: Tenant B attempts to use Tenant A's transaction token -> Blocked with 403
    hdr_b = auth_headers(env["admin_b"])
    res3 = client.post("/api/v1/payments", json=pay_payload, headers=hdr_b)
    assert res3.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)


def test_undercollateralized_payout_disbursement_blocked(client, db_session, auth_headers):
    """Attack 6: Attempting to disburse prize money before required sureties are approved."""
    env = setup_multi_tenant_environment(db_session)
    hdr_a = auth_headers(env["admin_a"])

    # Create auction and payout in PENDING_SURETY status
    auc = Auction(
        chit_group_id=env["group_a"].id,
        month_number=1,
        scheduled_at=datetime.now(timezone.utc),
        status=AuctionStatus.CLOSED,
        winning_membership_id=env["ticket_a"].id,
        winning_bid_discount=Decimal("20000.00"),
        foreman_commission=Decimal("5000.00"),
    )
    db_session.add(auc)
    db_session.flush()

    payout = Payout(
        auction_id=auc.id,
        chit_membership_id=env["ticket_a"].id,
        gross_prize_amount=Decimal("80000.00"),
        net_disbursed_amount=Decimal("80000.00"),
        disbursement_status=PayoutStatus.PENDING_SURETY,
    )
    db_session.add(payout)
    db_session.commit()

    # Attempt to disburse without approved sureties
    disburse_payload = {
        "disbursement_reference": "NEFT-UNAUTHORIZED-01",
        "foreman_charges_deducted": 0,
        "auto_clear_arrears": False,
    }
    res = client.post(f"/api/v1/payouts/{payout.id}/disburse", json=disburse_payload, headers=hdr_a)
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "sureties" in res.json()["detail"].lower() or "status" in res.json()["detail"].lower()
