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


def setup_payout_fixture(db_session):
    """Sets up an organization, branch, active chit circle, 5 subscribers, and concluded auction."""
    org = Organization(name="Payout Org", registration_number=f"REG-PAYOUT-{uuid.uuid4().hex[:6]}")
    db_session.add(org)
    db_session.commit()

    branch = Branch(organization_id=org.id, name="Payout Branch", branch_code=f"PB-{uuid.uuid4().hex[:4]}")
    db_session.add(branch)
    db_session.commit()

    manager = User(
        organization_id=org.id,
        branch_id=branch.id,
        full_name="Payout Branch Manager",
        email=f"mgr_payout_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919800000999",
        password_hash=get_password_hash("password123"),
        role=UserRole.ORG_ADMIN,
        kyc_status=KYCStatus.VERIFIED,
    )
    db_session.add(manager)
    db_session.commit()

    scheme = ChitScheme(
        organization_id=org.id,
        name="Scheme 100K 5M",
        total_value=Decimal("100000.00"),
        duration_months=5,
        monthly_installment=Decimal("20000.00"),
        foreman_commission_pct=Decimal("5.00"),
        min_bid_discount_pct=Decimal("5.00"),
        max_bid_discount_pct=Decimal("30.00"),
        foreman_month_one_reserved=False,
        is_active=True,
    )
    db_session.add(scheme)
    db_session.commit()

    group = ChitGroup(
        organization_id=org.id,
        branch_id=branch.id,
        scheme_id=scheme.id,
        manager_id=manager.id,
        group_code=f"GRP-PAYOUT-{uuid.uuid4().hex[:4]}",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 11, 30),
        current_month=1,
        auction_day_of_month=15,
        auction_time=time(16, 0),
        status=ChitGroupStatus.ACTIVE,
    )
    db_session.add(group)
    db_session.commit()

    subscribers = []
    memberships = []
    installments = []
    for i in range(1, 6):
        sub = User(
            organization_id=org.id,
            branch_id=branch.id,
            full_name=f"Subscriber Winner {i}",
            email=f"sub_winner_{i}_{uuid.uuid4().hex[:6]}@example.com",
            phone=f"+9198765400{i:02d}",
            password_hash=get_password_hash("password123"),
            role=UserRole.SUBSCRIBER,
            kyc_status=KYCStatus.VERIFIED,
        )
        db_session.add(sub)
        db_session.commit()

        mem = ChitMembership(
            chit_group_id=group.id,
            user_id=sub.id,
            ticket_number=i,
            status=MembershipStatus.ACTIVE,
        )
        db_session.add(mem)
        db_session.commit()

        inst = Installment(
            chit_group_id=group.id,
            chit_membership_id=mem.id,
            month_number=1,
            due_date=date(2026, 7, 1),
            gross_amount=Decimal("20000.00"),
            dividend_amount=Decimal("0.00"),
            penalty_amount=Decimal("0.00"),
            net_due_amount=Decimal("20000.00"),
            paid_amount=Decimal("0.00"),
            status=InstallmentStatus.UNPAID,
        )
        db_session.add(inst)
        db_session.commit()

        subscribers.append(sub)
        memberships.append(mem)
        installments.append(inst)

    # Concluded Month 1 Auction won by Subscriber 1 (Ticket #1)
    auction = Auction(
        chit_group_id=group.id,
        month_number=1,
        scheduled_at=datetime(2026, 7, 15, 16, 0, tzinfo=timezone.utc),
        opened_at=datetime(2026, 7, 15, 16, 0, tzinfo=timezone.utc),
        closed_at=datetime(2026, 7, 15, 17, 0, tzinfo=timezone.utc),
        status=AuctionStatus.CLOSED,
        is_foreman_month=False,
        winning_membership_id=memberships[0].id,
        winning_bid_discount=Decimal("20000.00"),
        foreman_commission=Decimal("5000.00"),
        total_dividend_pool=Decimal("15000.00"),
        dividend_per_ticket=Decimal("3000.00"),
        net_payable_installment=Decimal("17000.00"),
    )
    db_session.add(auction)
    memberships[0].status = MembershipStatus.PRIZED
    db_session.commit()

    return {
        "org": org,
        "branch": branch,
        "manager": manager,
        "group": group,
        "scheme": scheme,
        "subscribers": subscribers,
        "memberships": memberships,
        "installments": installments,
        "auction": auction,
    }


def test_payout_initialization_on_auction(client, db_session, auth_headers):
    """Fetch or create prize payout for concluded auction, starting in PENDING_SURETY."""
    data = setup_payout_fixture(db_session)
    mgr = data["manager"]
    auction = data["auction"]

    resp = client.get(f"/api/v1/payouts/auction/{auction.id}", headers=auth_headers(mgr))
    assert resp.status_code == status.HTTP_200_OK
    detail = resp.json()

    assert detail["ticket_number"] == 1
    assert float(detail["gross_prize_amount"]) == 80000.00  # 100K pot - 20K discount
    assert detail["disbursement_status"] == "PENDING_SURETY"
    assert detail["unpaid_installments_count"] == 1
    assert float(detail["unpaid_installments_amount"]) == 20000.00


def test_surety_lifecycle_add_and_verify(client, db_session, auth_headers):
    """Subscriber lodges salary guarantor surety, manager verifies it, and payout becomes SURETY_APPROVED."""
    data = setup_payout_fixture(db_session)
    mgr = data["manager"]
    sub1 = data["subscribers"][0]
    auction = data["auction"]

    payout_res = client.get(f"/api/v1/payouts/auction/{auction.id}", headers=auth_headers(mgr))
    payout_id = payout_res.json()["id"]

    # Subscriber submits guarantor surety
    surety_payload = {
        "surety_type": "SALARY_CERTIFICATE",
        "guarantor_name": "Suresh Raina (Govt Employee)",
        "guarantor_phone": "+919876001122",
        "document_reference": "SAL-CERT-2026-99",
        "remarks": "Monthly salary ₹85,000 at Railways",
    }
    resp_surety = client.post(
        f"/api/v1/payouts/{payout_id}/sureties",
        json=surety_payload,
        headers=auth_headers(sub1),
    )
    assert resp_surety.status_code == status.HTTP_201_CREATED
    surety_data = resp_surety.json()
    assert surety_data["verification_status"] == "PENDING"
    surety_id = surety_data["id"]

    # Manager verifies surety
    resp_verify = client.patch(
        f"/api/v1/payouts/sureties/{surety_id}/verify",
        json={"verification_status": "VERIFIED", "remarks": "Salary slips and employment certificate authenticated."},
        headers=auth_headers(mgr),
    )
    assert resp_verify.status_code == status.HTTP_200_OK
    assert resp_verify.json()["verification_status"] == "VERIFIED"

    # Payout should now be SURETY_APPROVED
    payout_check = client.get(f"/api/v1/payouts/auction/{auction.id}", headers=auth_headers(mgr))
    assert payout_check.json()["disbursement_status"] == "SURETY_APPROVED"


def test_unverified_surety_blocks_disbursement(client, db_session, auth_headers):
    """Disbursement attempt fails with 400 if sureties are still PENDING_SURETY."""
    data = setup_payout_fixture(db_session)
    mgr = data["manager"]
    auction = data["auction"]

    payout_res = client.get(f"/api/v1/payouts/auction/{auction.id}", headers=auth_headers(mgr))
    payout_id = payout_res.json()["id"]

    disburse_payload = {
        "disbursement_reference": "NEFT-ERR-001",
        "foreman_charges_deducted": 0.00,
        "auto_clear_arrears": True,
    }
    resp_disburse = client.post(
        f"/api/v1/payouts/{payout_id}/disburse",
        json=disburse_payload,
        headers=auth_headers(mgr),
    )
    assert resp_disburse.status_code == status.HTTP_400_BAD_REQUEST
    assert "Surety collateral is not approved" in resp_disburse.json()["detail"]


def test_disbursement_with_auto_arrears_deduction(client, db_session, auth_headers):
    """Disbursement automatically deducts ticket arrears and clears unpaid installments in the ledger."""
    data = setup_payout_fixture(db_session)
    mgr = data["manager"]
    sub1 = data["subscribers"][0]
    auction = data["auction"]
    inst1 = data["installments"][0]

    # Get payout and add + verify surety
    payout_res = client.get(f"/api/v1/payouts/auction/{auction.id}", headers=auth_headers(mgr))
    payout_id = payout_res.json()["id"]

    surety_res = client.post(
        f"/api/v1/payouts/{payout_id}/sureties",
        json={
            "surety_type": "PROPERTY_COLLATERAL",
            "document_reference": "TITLE-DEED-440",
            "remarks": "Title deed of commercial shop",
        },
        headers=auth_headers(sub1),
    )
    surety_id = surety_res.json()["id"]
    client.patch(
        f"/api/v1/payouts/sureties/{surety_id}/verify",
        json={"verification_status": "VERIFIED"},
        headers=auth_headers(mgr),
    )

    # Disburse with auto_clear_arrears = True
    disburse_payload = {
        "disbursement_reference": "NEFT-RTGS-99088",
        "foreman_charges_deducted": 500.00,  # documentation fee
        "auto_clear_arrears": True,
    }
    resp = client.post(
        f"/api/v1/payouts/{payout_id}/disburse",
        json=disburse_payload,
        headers=auth_headers(mgr),
    )
    assert resp.status_code == status.HTTP_200_OK
    disbursed = resp.json()

    # Math Verification:
    # Gross Prize = ₹80,000.
    # Month 1 Arrears = ₹20,000.
    # Foreman Charges = ₹500.
    # Net Disbursed = 80,000 - 20,000 - 500 = ₹59,500.
    assert float(disbursed["gross_prize_amount"]) == 80000.00
    assert float(disbursed["arrears_deducted"]) == 20000.00
    assert float(disbursed["foreman_charges_deducted"]) == 500.00
    assert float(disbursed["net_disbursed_amount"]) == 59500.00
    assert disbursed["disbursement_status"] == "DISBURSED"
    assert disbursed["disbursement_reference"] == "NEFT-RTGS-99088"

    # Verify that Month 1 Installment was automatically marked as PAID!
    db_session.refresh(inst1)
    assert inst1.status == InstallmentStatus.PAID
    assert inst1.paid_amount == Decimal("20000.00")


def test_substitute_defaulter_calculation(client, db_session, auth_headers):
    """Substitute a non-prized defaulting subscriber with a new KYC-verified member and compute statutory refund."""
    data = setup_payout_fixture(db_session)
    mgr = data["manager"]
    org = data["org"]
    branch = data["branch"]
    mem2 = data["memberships"][1]  # Ticket #2 (Unprized)
    inst2 = data["installments"][1]

    # Old member paid ₹10,000 partial payment
    inst2.paid_amount = Decimal("10000.00")
    inst2.status = InstallmentStatus.PARTIALLY_PAID
    db_session.commit()

    # Create new KYC-verified replacement user
    replacement_user = User(
        organization_id=org.id,
        branch_id=branch.id,
        full_name="New Replacement Member",
        email=f"rep_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919876599999",
        password_hash=get_password_hash("password123"),
        role=UserRole.SUBSCRIBER,
        kyc_status=KYCStatus.VERIFIED,
    )
    db_session.add(replacement_user)
    db_session.commit()

    # Manager executes substitution
    sub_payload = {
        "chit_membership_id": str(mem2.id),
        "new_user_id": str(replacement_user.id),
        "reason": "Defaulted for 3 consecutive cycles.",
    }
    resp_sub = client.post("/api/v1/payouts/substitute", json=sub_payload, headers=auth_headers(mgr))
    assert resp_sub.status_code == status.HTTP_200_OK
    stmt = resp_sub.json()

    # Math Verification:
    # Total Paid = ₹10,000.
    # Foreman Commission = 5% of 100K = ₹5,000.
    # Penalties = ₹0.
    # Statutory Refund = 10,000 - 5,000 = ₹5,000.
    assert float(stmt["total_paid_by_old_member"]) == 10000.00
    assert float(stmt["foreman_commission_deduction"]) == 5000.00
    assert float(stmt["statutory_refund_amount"]) == 5000.00
    assert stmt["status"] == "SUBSTITUTED_AND_TRANSFERRED"

    # Verify membership now belongs to the replacement user
    db_session.refresh(mem2)
    assert mem2.user_id == replacement_user.id
    assert mem2.status == MembershipStatus.ACTIVE
