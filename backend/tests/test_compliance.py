import uuid
from datetime import date, time, datetime, timezone, timedelta
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
from app.models.payout import Payout, PayoutStatus
from app.models.compliance import SecurityDeposit, RegistrarFiling, DepositType, LienStatus, FilingType, FilingStatus
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


def setup_compliance_fixture(db_session):
    """Sets up an organization, branch, active chit circle, 5 subscribers, and concluded auction."""
    org = Organization(name="Compliance Org", registration_number=f"REG-COMP-{uuid.uuid4().hex[:6]}")
    db_session.add(org)
    db_session.commit()

    branch = Branch(organization_id=org.id, name="Compliance Branch", branch_code=f"CB-{uuid.uuid4().hex[:4]}", address="Hyderabad")
    db_session.add(branch)
    db_session.commit()

    manager = User(
        organization_id=org.id,
        branch_id=branch.id,
        full_name="Compliance Manager",
        email=f"mgr_comp_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919800000888",
        password_hash=get_password_hash("password123"),
        role=UserRole.BRANCH_MANAGER,
        kyc_status=KYCStatus.VERIFIED,
    )
    admin = User(
        organization_id=org.id,
        branch_id=branch.id,
        full_name="Compliance Org Admin",
        email=f"admin_comp_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919800000777",
        password_hash=get_password_hash("password123"),
        role=UserRole.ORG_ADMIN,
        kyc_status=KYCStatus.VERIFIED,
    )
    db_session.add_all([manager, admin])
    db_session.commit()

    scheme = ChitScheme(
        organization_id=org.id,
        name="Scheme 100K 5M Comp",
        total_value=Decimal("100000.00"),
        duration_months=5,
        monthly_installment=Decimal("20000.00"),
        foreman_commission_pct=Decimal("5.00"),
        max_bid_discount_pct=Decimal("30.00"),
        min_bid_discount_pct=Decimal("5.00"),
        foreman_month_one_reserved=False,
    )
    db_session.add(scheme)
    db_session.commit()

    group = ChitGroup(
        organization_id=org.id,
        branch_id=branch.id,
        scheme_id=scheme.id,
        group_code=f"COMP-GRP-{uuid.uuid4().hex[:4]}",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 1),
        current_month=1,
        auction_day_of_month=10,
        auction_time=time(16, 0),
        status=ChitGroupStatus.ACTIVE,
    )
    db_session.add(group)
    db_session.commit()

    # 5 subscribers
    subscribers = []
    memberships = []
    for i in range(1, 6):
        sub = User(
            organization_id=org.id,
            branch_id=branch.id,
            full_name=f"Subscriber {i}",
            email=f"sub_comp_{i}_{uuid.uuid4().hex[:4]}@example.com",
            phone=f"+91981110000{i}",
            password_hash=get_password_hash("password123"),
            role=UserRole.SUBSCRIBER,
            kyc_status=KYCStatus.VERIFIED,
        )
        db_session.add(sub)
        db_session.flush()
        subscribers.append(sub)

        mem = ChitMembership(
            chit_group_id=group.id,
            user_id=sub.id,
            ticket_number=i,
            status=MembershipStatus.ACTIVE,
        )
        db_session.add(mem)
        db_session.flush()
        memberships.append(mem)

        # Month 1 installment
        inst = Installment(
            chit_group_id=group.id,
            chit_membership_id=mem.id,
            month_number=1,
            due_date=date(2026, 1, 10),
            gross_amount=Decimal("20000.00"),
            dividend_amount=Decimal("0.00"),
            penalty_amount=Decimal("0.00"),
            net_due_amount=Decimal("20000.00"),
            paid_amount=Decimal("20000.00") if i == 1 else Decimal("0.00"),
            status=InstallmentStatus.PAID if i == 1 else InstallmentStatus.UNPAID,
        )
        db_session.add(inst)

    db_session.commit()

    # Concluded auction month 1
    auction = Auction(
        chit_group_id=group.id,
        month_number=1,
        scheduled_at=datetime.now(timezone.utc),
        opened_at=datetime.now(timezone.utc),
        closed_at=datetime.now(timezone.utc),
        status=AuctionStatus.CLOSED,
        winning_membership_id=memberships[0].id,
        winning_bid_discount=Decimal("20000.00"),
        foreman_commission=Decimal("5000.00"),
        total_dividend_pool=Decimal("15000.00"),
        dividend_per_ticket=Decimal("3000.00"),
        net_payable_installment=Decimal("17000.00"),
    )
    db_session.add(auction)
    db_session.flush()

    # Place a bid
    bid = Bid(
        auction_id=auction.id,
        chit_membership_id=memberships[0].id,
        bid_discount_amount=Decimal("20000.00"),
    )
    db_session.add(bid)

    # Disbursed payout
    payout = Payout(
        auction_id=auction.id,
        chit_membership_id=memberships[0].id,
        gross_prize_amount=Decimal("80000.00"),
        foreman_charges_deducted=Decimal("500.00"),
        arrears_deducted=Decimal("0.00"),
        net_disbursed_amount=Decimal("79500.00"),
        disbursement_status=PayoutStatus.DISBURSED,
        disbursement_reference="UTR-COMP-9999",
        disbursed_at=datetime.now(timezone.utc),
    )
    db_session.add(payout)
    db_session.commit()

    return {
        "org": org,
        "branch": branch,
        "manager": manager,
        "admin": admin,
        "scheme": scheme,
        "group": group,
        "subscribers": subscribers,
        "memberships": memberships,
        "auction": auction,
        "payout": payout,
    }


def test_section_20_security_deposit_lifecycle(client, db_session, auth_headers):
    """Verify Section 20 statutory deposit lodging, 100% chit value validation, and lien pledge."""
    f = setup_compliance_fixture(db_session)
    admin_hdr = auth_headers(f["admin"])

    # 1. Attempt to lodge deposit LESS than 100% of chit value -> Must fail under Section 20
    bad_payload = {
        "group_id": str(f["group"].id),
        "deposit_type": "FIXED_DEPOSIT",
        "bank_name": "State Bank of India",
        "account_or_fdr_number": "FDR-123456",
        "amount": 50000.00,  # Scheme total value is 100,000
        "deposit_date": str(date(2026, 1, 1)),
        "maturity_date": str(date(2026, 12, 31)),
        "registrar_order_reference": "REG-ORDER-HYD-001",
    }
    res = client.post("/api/v1/compliance/deposits", json=bad_payload, headers=admin_hdr)
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "100% of the chit value" in res.json()["detail"]

    # 2. Lodge compliant deposit (100,000.00)
    good_payload = {
        "group_id": str(f["group"].id),
        "deposit_type": "FIXED_DEPOSIT",
        "bank_name": "State Bank of India",
        "account_or_fdr_number": "FDR-SBI-998877",
        "amount": 100000.00,
        "deposit_date": str(date(2026, 1, 1)),
        "maturity_date": str(date(2026, 12, 31)),
        "registrar_order_reference": "REG-ORDER-HYD-001",
        "remarks": "100% Chit Value Section 20 Security Pledge",
    }
    res = client.post("/api/v1/compliance/deposits", json=good_payload, headers=admin_hdr)
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    deposit_id = data["id"]
    assert data["lien_status"] == "PENDING"
    assert Decimal(str(data["amount"])) == Decimal("100000.00")

    # 3. Verify / Pledge the lien
    res_verify = client.patch(
        f"/api/v1/compliance/deposits/{deposit_id}/verify",
        json={"lien_status": "PLEDGED", "remarks": "Lien noted in favor of Registrar of Chits"},
        headers=admin_hdr,
    )
    assert res_verify.status_code == status.HTTP_200_OK
    assert res_verify.json()["lien_status"] == "PLEDGED"

    # 4. List deposits
    res_list = client.get("/api/v1/compliance/deposits", headers=admin_hdr)
    assert res_list.status_code == status.HTTP_200_OK
    items = res_list.json()
    assert len(items) >= 1
    assert any(x["id"] == deposit_id and x["lien_status"] == "PLEDGED" for x in items)


def test_statutory_form_xiv_generation(client, db_session, auth_headers):
    """Verify statutory Form XIV Minutes generation with exact dividend and discount math."""
    f = setup_compliance_fixture(db_session)
    admin_hdr = auth_headers(f["admin"])

    res = client.get(f"/api/v1/compliance/auctions/{f['auction'].id}/form-xiv", headers=admin_hdr)
    assert res.status_code == status.HTTP_200_OK
    form_data = res.json()

    assert form_data["chit_group_code"] == f["group"].group_code
    assert form_data["auction_round"] == 1
    assert Decimal(str(form_data["chit_value"])) == Decimal("100000.00")
    assert Decimal(str(form_data["winning_bid_discount"])) == Decimal("20000.00")
    assert Decimal(str(form_data["prized_amount"])) == Decimal("80000.00")
    assert Decimal(str(form_data["foreman_commission"])) == Decimal("5000.00")
    assert Decimal(str(form_data["dividend_total"])) == Decimal("15000.00")
    assert Decimal(str(form_data["dividend_per_ticket"])) == Decimal("3000.00")
    assert form_data["prized_ticket_number"] == 1
    assert "Subscriber 1" in form_data["prized_subscriber_name"]
    assert len(form_data["bids_recorded"]) >= 1


def test_record_registrar_filing_and_acknowledgment(client, db_session, auth_headers):
    """Verify submitting Form XIV and updating acknowledgment from the Registrar Office."""
    f = setup_compliance_fixture(db_session)
    admin_hdr = auth_headers(f["admin"])

    filing_payload = {
        "group_id": str(f["group"].id),
        "auction_id": str(f["auction"].id),
        "form_type": "FORM_XIV_MINUTES",
        "filing_reference_number": f"REG-XIV-{uuid.uuid4().hex[:6]}",
        "filed_date": str(date(2026, 1, 15)),
        "registrar_office_name": "Office of Deputy Registrar of Chits, Hyderabad Central",
        "notes": "Auction month 1 minutes submitted physically and online.",
    }
    res = client.post("/api/v1/compliance/filings", json=filing_payload, headers=admin_hdr)
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    filing_id = data["id"]
    assert data["form_type"] == "FORM_XIV_MINUTES"
    assert data["status"] == "DRAFT"
    assert data["metadata_payload"] is not None

    # Update with registrar acknowledgment
    ack_res = client.patch(
        f"/api/v1/compliance/filings/{filing_id}",
        json={"acknowledgment_number": "ACK-REG-2026-98765", "notes": "Acknowledged and sealed by Registrar."},
        headers=admin_hdr,
    )
    assert ack_res.status_code == status.HTTP_200_OK
    assert ack_res.json()["status"] == "ACKNOWLEDGED"
    assert ack_res.json()["acknowledgment_number"] == "ACK-REG-2026-98765"


def test_circle_financial_balance_sheet_reconciliation(client, db_session, auth_headers):
    """Verify double-entry balance sheet balances inflows, prize disbursements, and pool balance."""
    f = setup_compliance_fixture(db_session)
    admin_hdr = auth_headers(f["admin"])

    # First pledge a deposit so sec_20_lien_pledged is present
    deposit = SecurityDeposit(
        organization_id=f["org"].id,
        group_id=f["group"].id,
        deposit_type=DepositType.FIXED_DEPOSIT,
        bank_name="HDFC Bank",
        account_or_fdr_number="HDFC-FDR-111",
        amount=Decimal("100000.00"),
        deposit_date=date(2026, 1, 1),
        maturity_date=date(2026, 12, 31),
        registrar_order_reference="REF-HDFC",
        lien_status=LienStatus.PLEDGED,
    )
    db_session.add(deposit)
    db_session.commit()

    res = client.get(f"/api/v1/compliance/groups/{f['group'].id}/balance-sheet", headers=admin_hdr)
    assert res.status_code == status.HTTP_200_OK
    sheet = res.json()

    assert sheet["group_code"] == f["group"].group_code
    assert Decimal(str(sheet["total_chit_value"])) == Decimal("100000.00")
    # Inflow: Ticket 1 paid 20,000 + doc fees 500 = 20,500
    assert Decimal(str(sheet["total_installments_collected"])) == Decimal("20000.00")
    assert Decimal(str(sheet["total_doc_fees_collected"])) == Decimal("500.00")
    assert Decimal(str(sheet["total_gross_inflow"])) == Decimal("20500.00")
    # Outflow: Payout net disbursed = 79,500
    assert Decimal(str(sheet["total_prize_money_disbursed"])) == Decimal("79500.00")
    # Arrears: 4 unpaid tickets of 20,000 = 80,000
    assert Decimal(str(sheet["current_arrears_receivable"])) == Decimal("80000.00")
    # Section 20 lien pledged
    assert Decimal(str(sheet["sec_20_lien_pledged"])) == Decimal("100000.00")
    assert sheet["is_balanced"] is True


def test_delinquency_aging_report(client, db_session, auth_headers):
    """Verify delinquency report accurately buckets unpaid installments into aging tiers."""
    f = setup_compliance_fixture(db_session)
    admin_hdr = auth_headers(f["admin"])

    res = client.get(f"/api/v1/compliance/groups/{f['group'].id}/delinquency-report", headers=admin_hdr)
    assert res.status_code == status.HTTP_200_OK
    report = res.json()

    assert report["group_code"] == f["group"].group_code
    assert report["total_defaulters_count"] == 4  # 4 subscribers haven't paid Month 1
    assert Decimal(str(report["total_delinquent_amount"])) == Decimal("80000.00")
    assert len(report["delinquent_tickets"]) == 4


def test_compliance_system_summary(client, db_session, auth_headers):
    """Verify organization-wide regulatory summary."""
    f = setup_compliance_fixture(db_session)
    admin_hdr = auth_headers(f["admin"])

    res = client.get("/api/v1/compliance/system-summary", headers=admin_hdr)
    assert res.status_code == status.HTTP_200_OK
    summary = res.json()
    assert "total_lien_pledged" in summary
    assert "active_circles_covered" in summary
    assert "total_filings_count" in summary
    assert "total_prize_disbursed" in summary
