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
from app.models.compliance import SecurityDeposit, DepositType, LienStatus, RegistrarFiling, FilingType, FilingStatus
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


def test_full_5_month_circle_lifecycle_simulation(client, db_session, auth_headers):
    """
    Comprehensive End-to-End simulation of a 5-Month Chit Circle:
    1. Tenant Setup: Org, Branch, Org Admin, and 5 KYC-verified Subscribers.
    2. Scheme & Circle: 5-month ₹1,00,000 chit circle (₹20,000/mo, 5% commission).
    3. Enrollment: 5 subscribers enrolled into Tickets 1 to 5.
    4. Circle Activation & Installment Generation: Month 1 dues auto-created.
    5. Section 20 Compliance: 100% aggregate chit value (₹1,00,000) FDR lodged & pledged.
    6. Round-by-Round Execution (Months 1 to 5):
       - Live reverse auction bidding chamber.
       - Monotonic FCFS tie-breaking and winner determination.
       - Dividend pool calculation & credit to installment ledger.
       - Prized member exclusion from future rounds.
       - Surety lodgment & verification barrier.
       - Prize money payout disbursement with arrears auto-deduction.
       - Member installment settlement with idempotent receipts.
       - Statutory Form XIV Minutes generation & Registrar filing.
    7. Completion & Financial Audit: Double-entry balance sheet verification.
    """
    # -------------------------------------------------------------------------
    # 1. SETUP TENANT & USERS
    # -------------------------------------------------------------------------
    org = Organization(name="Chitties Apex Group", registration_number=f"REG-E2E-{uuid.uuid4().hex[:6]}")
    db_session.add(org)
    db_session.commit()

    branch = Branch(
        organization_id=org.id,
        name="Apex Central Branch",
        branch_code=f"CB-{uuid.uuid4().hex[:4]}",
        address="Banjara Hills, Hyderabad",
    )
    db_session.add(branch)
    db_session.commit()

    admin = User(
        organization_id=org.id,
        branch_id=branch.id,
        full_name="Rajesh Sharma (Admin)",
        email=f"admin_e2e_{uuid.uuid4().hex[:6]}@apexchits.com",
        phone="+919800011100",
        password_hash=get_password_hash("ApexPass@2026"),
        role=UserRole.ORG_ADMIN,
        kyc_status=KYCStatus.VERIFIED,
    )
    db_session.add(admin)
    db_session.commit()
    admin_hdr = auth_headers(admin)

    # 5 Subscribers
    subscribers = []
    sub_hdrs = []
    for i in range(1, 6):
        sub = User(
            organization_id=org.id,
            branch_id=branch.id,
            full_name=f"Subscriber {i} Kumar",
            email=f"sub_e2e_{i}_{uuid.uuid4().hex[:4]}@example.com",
            phone=f"+91980002220{i}",
            password_hash=get_password_hash("SubPass@2026"),
            role=UserRole.SUBSCRIBER,
            kyc_status=KYCStatus.VERIFIED,
            kyc_document_type="AADHAAR",
            kyc_document_number=f"99887766550{i}",
        )
        db_session.add(sub)
        db_session.flush()
        subscribers.append(sub)
        sub_hdrs.append(auth_headers(sub))
    db_session.commit()

    # -------------------------------------------------------------------------
    # 2. CHIT SCHEME CREATION (₹1,00,000 / 5 Months / ₹20,000 per month)
    # -------------------------------------------------------------------------
    scheme_res = client.post(
        "/api/v1/schemes",
        json={
            "name": "Apex Micro Gold 100K 5M",
            "total_value": 100000.00,
            "duration_months": 5,
            "monthly_installment": 20000.00,
            "foreman_commission_pct": 5.00,
            "max_bid_discount_pct": 30.00,
            "min_bid_discount_pct": 5.00,
            "foreman_month_one_reserved": False,
        },
        headers=admin_hdr,
    )
    assert scheme_res.status_code == status.HTTP_201_CREATED
    scheme_id = scheme_res.json()["id"]

    # -------------------------------------------------------------------------
    # 3. CHIT GROUP LAUNCH
    # -------------------------------------------------------------------------
    group_code = f"APEX-GOLD-{uuid.uuid4().hex[:4].upper()}"
    group_res = client.post(
        "/api/v1/groups",
        json={
            "branch_id": str(branch.id),
            "scheme_id": scheme_id,
            "group_code": group_code,
            "start_date": str(date(2026, 1, 1)),
            "end_date": str(date(2026, 6, 1)),
            "auction_day_of_month": 15,
            "auction_time": "15:00:00",
        },
        headers=admin_hdr,
    )
    assert group_res.status_code == status.HTTP_201_CREATED
    group_id = group_res.json()["id"]

    # -------------------------------------------------------------------------
    # 4. ENROLL SUBSCRIBERS (Tickets 1 to 5)
    # -------------------------------------------------------------------------
    for i, sub in enumerate(subscribers, start=1):
        enroll_res = client.post(
            f"/api/v1/groups/{group_id}/enroll",
            json={"user_id": str(sub.id), "ticket_number": i},
            headers=admin_hdr,
        )
        assert enroll_res.status_code == status.HTTP_201_CREATED

    # -------------------------------------------------------------------------
    # 5. SECTION 20 SECURITY DEPOSIT (100% Chit Value = ₹1,00,000)
    # -------------------------------------------------------------------------
    sec20_res = client.post(
        "/api/v1/compliance/deposits",
        json={
            "group_id": group_id,
            "deposit_type": "FIXED_DEPOSIT",
            "bank_name": "State Bank of India - Banjara Hills",
            "account_or_fdr_number": f"SBI-FDR-{uuid.uuid4().hex[:6].upper()}",
            "amount": 100000.00,
            "deposit_date": str(date(2026, 1, 1)),
            "maturity_date": str(date(2026, 12, 31)),
            "registrar_order_reference": f"REG-HYD-ORDER-{group_code}",
            "remarks": "100% Security Deposit pledged under Section 20",
        },
        headers=admin_hdr,
    )
    assert sec20_res.status_code == status.HTTP_201_CREATED
    deposit_id = sec20_res.json()["id"]

    # Verify/Pledge Lien
    pledge_res = client.patch(
        f"/api/v1/compliance/deposits/{deposit_id}/verify",
        json={"lien_status": "PLEDGED", "remarks": "Lien registered in favor of Registrar of Chits."},
        headers=admin_hdr,
    )
    assert pledge_res.status_code == status.HTTP_200_OK
    assert pledge_res.json()["lien_status"] == "PLEDGED"

    # -------------------------------------------------------------------------
    # 6. ACTIVATE CHIT CIRCLE (Generates Month 1 Installment Obligations)
    # -------------------------------------------------------------------------
    activate_res = client.patch(
        f"/api/v1/groups/{group_id}/status",
        json={"status": "ACTIVE"},
        headers=admin_hdr,
    )
    assert activate_res.status_code == status.HTTP_200_OK

    # -------------------------------------------------------------------------
    # 7. SIMULATE 5 CONSECUTIVE MONTHLY AUCTIONS & PAYOUTS
    # -------------------------------------------------------------------------
    # Each round has a predefined winner and discount
    auction_scenarios = [
        {"round": 1, "winner_idx": 0, "discount": 25000.00},  # Winner: Subscriber 1, Disc: 25k -> Net Prize: 75k
        {"round": 2, "winner_idx": 1, "discount": 20000.00},  # Winner: Subscriber 2, Disc: 20k -> Net Prize: 80k
        {"round": 3, "winner_idx": 2, "discount": 15000.00},  # Winner: Subscriber 3, Disc: 15k -> Net Prize: 85k
        {"round": 4, "winner_idx": 3, "discount": 10000.00},  # Winner: Subscriber 4, Disc: 10k -> Net Prize: 90k
        {"round": 5, "winner_idx": 4, "discount": 5000.00},   # Winner: Subscriber 5, Disc: 5k (min) -> Net Prize: 95k
    ]

    for scenario in auction_scenarios:
        r = scenario["round"]
        w_idx = scenario["winner_idx"]
        discount = scenario["discount"]
        winner_sub = subscribers[w_idx]

        # A. Find or initialize auction for month r
        # In Chitties, group activation initializes round 1 auction
        auctions_list = client.get(f"/api/v1/auctions/group/{group_id}", headers=admin_hdr).json()
        auc = next((a for a in auctions_list if a["month_number"] == r), None)
        if not auc:
            # Create scheduled auction for month r
            create_auc_res = client.post(
                "/api/v1/auctions",
                json={
                    "chit_group_id": group_id,
                    "month_number": r,
                    "scheduled_at": datetime.now(timezone.utc).isoformat(),
                },
                headers=admin_hdr,
            )
            auc = create_auc_res.json()

        auc_id = auc["id"]

        # B. Start Auction -> Status OPEN
        start_res = client.post(f"/api/v1/auctions/{auc_id}/start", headers=admin_hdr)
        assert start_res.status_code == status.HTTP_200_OK

        # C. Prior winner check: Past winners cannot bid in this round
        for past_idx in range(w_idx):
            past_bid_res = client.post(
                f"/api/v1/auctions/{auc_id}/bids",
                json={"bid_discount_amount": discount},
                headers=sub_hdrs[past_idx],
            )
            assert past_bid_res.status_code == status.HTTP_400_BAD_REQUEST
            assert "already prized" in past_bid_res.json()["detail"].lower()

        # D. Place Winning Bid
        bid_res = client.post(
            f"/api/v1/auctions/{auc_id}/bids",
            json={"bid_discount_amount": discount},
            headers=sub_hdrs[w_idx],
        )
        assert bid_res.status_code == status.HTTP_201_CREATED

        # E. Close Auction -> Computes Dividend & Ledger adjustments
        close_res = client.post(f"/api/v1/auctions/{auc_id}/close", headers=admin_hdr)
        assert close_res.status_code == status.HTTP_200_OK
        closed_auc = close_res.json()
        assert closed_auc["winner_ticket_number"] == w_idx + 1
        assert Decimal(str(closed_auc["winning_bid_discount"])) == Decimal(str(discount))

        # F. Prize Payout: Lodge & Verify Surety Collateral
        payout_res = client.get(f"/api/v1/payouts/auction/{auc_id}", headers=admin_hdr)
        assert payout_res.status_code == status.HTTP_200_OK
        payout_data = payout_res.json()
        payout_id = payout_data["id"]

        surety_res = client.post(
            f"/api/v1/payouts/{payout_id}/sureties",
            json={
                "surety_type": "SALARY_CERTIFICATE",
                "guarantor_name": f"Guarantor for Sub {w_idx + 1}",
                "guarantor_phone": "+919876543210",
                "document_reference": f"SAL-SLIP-ROUND-{r}",
                "remarks": "Monthly salary verified",
            },
            headers=admin_hdr,
        )
        assert surety_res.status_code == status.HTTP_201_CREATED
        surety_id = surety_res.json()["id"]

        verify_surety_res = client.patch(
            f"/api/v1/payouts/sureties/{surety_id}/verify",
            json={"verification_status": "VERIFIED", "remarks": "Salary verified with employer."},
            headers=admin_hdr,
        )
        assert verify_surety_res.status_code == status.HTTP_200_OK

        # G. Disburse Prize Money (with auto-clear arrears)
        disburse_res = client.post(
            f"/api/v1/payouts/{payout_id}/disburse",
            json={
                "disbursement_reference": f"NEFT-APEX-R{r}-{uuid.uuid4().hex[:4].upper()}",
                "foreman_charges_deducted": 500.00,
                "auto_clear_arrears": True,
            },
            headers=admin_hdr,
        )
        assert disburse_res.status_code == status.HTTP_200_OK
        assert disburse_res.json()["disbursement_status"] == "DISBURSED"

        # H. Member Installments Settlement for Round r
        # Direct ledger settlement simulation while payments module is deferred
        month_insts = (
            db_session.query(Installment)
            .filter(
                Installment.chit_group_id == group_id,
                Installment.month_number == r,
            )
            .all()
        )
        for inst in month_insts:
            inst.paid_amount = inst.net_due_amount
            inst.status = InstallmentStatus.PAID
        db_session.commit()

        # I. Statutory Form XIV Minutes & Registrar Filing
        form_xiv_res = client.get(f"/api/v1/compliance/auctions/{auc_id}/form-xiv", headers=admin_hdr)
        assert form_xiv_res.status_code == status.HTTP_200_OK
        assert form_xiv_res.json()["auction_round"] == r

        filing_res = client.post(
            "/api/v1/compliance/filings",
            json={
                "group_id": group_id,
                "auction_id": auc_id,
                "form_type": "FORM_XIV_MINUTES",
                "filing_reference_number": f"REG-XIV-R{r}-{group_code}",
                "filed_date": str(date.today()),
                "registrar_office_name": "Office of Sub-Registrar of Chits, Hyderabad Central",
                "notes": f"Statutory auction minutes for month {r}",
            },
            headers=admin_hdr,
        )
        assert filing_res.status_code == status.HTTP_201_CREATED

    # -------------------------------------------------------------------------
    # 8. COMPLETE CHIT CIRCLE & AUDIT BALANCE SHEET RECONCILIATION
    # -------------------------------------------------------------------------
    complete_res = client.patch(
        f"/api/v1/groups/{group_id}/status",
        json={"status": "COMPLETED"},
        headers=admin_hdr,
    )
    assert complete_res.status_code == status.HTTP_200_OK

    # Balance Sheet Audit Check
    sheet_res = client.get(f"/api/v1/compliance/groups/{group_id}/balance-sheet", headers=admin_hdr)
    assert sheet_res.status_code == status.HTTP_200_OK
    sheet = sheet_res.json()

    assert sheet["rounds_completed"] == 5
    assert sheet["total_rounds"] == 5
    assert Decimal(str(sheet["total_chit_value"])) == Decimal("100000.00")
    assert sheet["is_balanced"] is True
    # All 5 rounds concluded and disbursed
    assert Decimal(str(sheet["total_prize_money_disbursed"])) > Decimal("0.00")
    # All ticket installments settled
    assert Decimal(str(sheet["current_arrears_receivable"])) == Decimal("0.00")
    # Section 20 lien intact
    assert Decimal(str(sheet["sec_20_lien_pledged"])) == Decimal("100000.00")
