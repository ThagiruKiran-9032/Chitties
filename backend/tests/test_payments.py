import uuid
from datetime import date, datetime, time, timezone
from decimal import Decimal
import pytest
from fastapi import status

from app.core.security import get_password_hash, create_access_token
from app.models.organization import Organization, Branch
from app.models.chit_scheme import ChitScheme
from app.models.chit_group import ChitGroup, ChitGroupStatus
from app.models.membership import ChitMembership, MembershipStatus
from app.models.installment import Installment, InstallmentStatus
from app.models.payment import Payment, PaymentMethod, PaymentStatus
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


def setup_payment_fixture(db_session):
    """Sets up an organization, branch, active chit group, and subscriber installments."""
    org = Organization(name="Payment Org", registration_number=f"REG-PAY-{uuid.uuid4().hex[:6]}")
    db_session.add(org)
    db_session.commit()

    branch = Branch(organization_id=org.id, name="Pay Branch", branch_code=f"PB-{uuid.uuid4().hex[:4]}")
    db_session.add(branch)
    db_session.commit()

    manager = User(
        organization_id=org.id,
        branch_id=branch.id,
        full_name="Branch Cashier Mgr",
        email=f"mgr_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919800000077",
        password_hash=get_password_hash("password123"),
        role=UserRole.ORG_ADMIN,
        kyc_status=KYCStatus.VERIFIED,
    )
    db_session.add(manager)
    db_session.commit()

    scheme = ChitScheme(
        organization_id=org.id,
        name="Scheme 60K 3M",
        total_value=Decimal("60000.00"),
        duration_months=3,
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
        group_code=f"GRP-PAY-{uuid.uuid4().hex[:4]}",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
        current_month=1,
        auction_day_of_month=10,
        auction_time=time(15, 0),
        status=ChitGroupStatus.ACTIVE,
    )
    db_session.add(group)
    db_session.commit()

    members = []
    installments = []
    for i in range(1, 4):
        sub = User(
            organization_id=org.id,
            branch_id=branch.id,
            full_name=f"Subscriber P{i}",
            email=f"sub_pay_{i}_{uuid.uuid4().hex[:6]}@example.com",
            phone=f"+9198765000{i:02d}",
            password_hash=get_password_hash("password123"),
            role=UserRole.SUBSCRIBER,
            kyc_status=KYCStatus.VERIFIED,
        )
        db_session.add(sub)
        db_session.commit()

        membership = ChitMembership(
            chit_group_id=group.id,
            user_id=sub.id,
            ticket_number=i,
            status=MembershipStatus.ACTIVE,
        )
        db_session.add(membership)
        db_session.commit()

        inst = Installment(
            chit_group_id=group.id,
            chit_membership_id=membership.id,
            month_number=1,
            due_date=date(2026, 6, 1),
            gross_amount=Decimal("20000.00"),
            dividend_amount=Decimal("0.00"),
            penalty_amount=Decimal("0.00"),
            net_due_amount=Decimal("20000.00"),
            paid_amount=Decimal("0.00"),
            status=InstallmentStatus.UNPAID,
        )
        db_session.add(inst)
        db_session.commit()

        members.append((sub, membership))
        installments.append(inst)

    return {
        "org": org,
        "branch": branch,
        "manager": manager,
        "group": group,
        "members": members,
        "installments": installments,
    }


def test_payment_endpoints_are_deactivated(client, db_session, auth_headers):
    """Confirm that payment endpoints are removed from active routing (HTTP 404)."""
    data = setup_payment_fixture(db_session)
    sub1, _ = data["members"][0]
    inst1 = data["installments"][0]

    resp = client.post(
        "/api/v1/payments",
        json={
            "installment_id": str(inst1.id),
            "amount": 20000.00,
            "payment_method": "UPI",
            "transaction_reference": f"UPI-TEST-{uuid.uuid4().hex[:8]}",
        },
        headers=auth_headers(sub1),
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND

    resp_list = client.get("/api/v1/payments", headers=auth_headers(sub1))
    assert resp_list.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.skip(reason="Payments module temporarily deferred; endpoints deactivated")
def test_process_payment_success_and_ledger_status(client, db_session, auth_headers):
    """Full installment payment transitions status to PAID and generates digital receipt."""
    pass


@pytest.mark.skip(reason="Payments module temporarily deferred; endpoints deactivated")
def test_payment_idempotency_guard(client, db_session, auth_headers):
    """Submitting the exact same transaction reference twice returns the original receipt without double-charging."""
    pass


@pytest.mark.skip(reason="Payments module temporarily deferred; endpoints deactivated")
def test_partial_payment_lifecycle(client, db_session, auth_headers):
    """Partial payments transition installment to PARTIALLY_PAID and subsequent payment finishes it."""
    pass


@pytest.mark.skip(reason="Payments module temporarily deferred; endpoints deactivated")
def test_overpayment_rejected(client, db_session, auth_headers):
    """Attempting to pay more than the outstanding balance is rejected."""
    pass


@pytest.mark.skip(reason="Payments module temporarily deferred; endpoints deactivated")
def test_cross_tenant_payment_blocked(client, db_session, auth_headers):
    """User belonging to Org B cannot pay installment in Org A."""
    pass


def test_apply_penalty_and_recalculate(client, db_session, auth_headers):
    """Manager levies an overdue penalty which increases net_due_amount."""
    data = setup_payment_fixture(db_session)
    mgr = data["manager"]
    inst1 = data["installments"][0]

    resp = client.post(
        f"/api/v1/installments/{inst1.id}/penalty",
        json={"penalty_amount": 500.00, "reason": "Late fee for 15-day delay"},
        headers=auth_headers(mgr),
    )
    assert resp.status_code == status.HTTP_200_OK
    detail = resp.json()

    assert float(detail["penalty_amount"]) == 500.00
    assert float(detail["net_due_amount"]) == 20500.00
    assert detail["status"] == "OVERDUE"


def test_member_ledger_summary(client, db_session, auth_headers):
    """Subscriber fetches full statement showing gross, dividends, penalties, paid, and balance."""
    data = setup_payment_fixture(db_session)
    sub1, mem1 = data["members"][0]
    inst1 = data["installments"][0]

    # Directly record partial payment into database to test statement aggregation while payments API is deferred
    inst1.paid_amount = Decimal("5000.00")
    inst1.status = InstallmentStatus.PARTIALLY_PAID
    payment = Payment(
        organization_id=data["org"].id,
        chit_membership_id=mem1.id,
        installment_id=inst1.id,
        amount_paid=Decimal("5000.00"),
        payment_method=PaymentMethod.UPI,
        transaction_reference=f"STMT-REF-{uuid.uuid4().hex[:6]}",
        receipt_number=f"REC-TEST-{uuid.uuid4().hex[:6]}",
        status=PaymentStatus.COMPLETED,
        recorded_by_user_id=sub1.id,
        paid_at=datetime.now(timezone.utc),
    )
    db_session.add(payment)
    db_session.commit()

    resp = client.get(f"/api/v1/installments/membership/{mem1.id}", headers=auth_headers(sub1))
    assert resp.status_code == status.HTTP_200_OK
    stmt = resp.json()

    assert stmt["ticket_number"] == 1
    assert float(stmt["total_gross_obligations"]) == 20000.00
    assert float(stmt["total_amount_paid"]) == 5000.00
    assert float(stmt["total_outstanding_balance"]) == 15000.00
    assert len(stmt["installments"]) == 1
    assert len(stmt["installments"][0]["payments"]) == 1
