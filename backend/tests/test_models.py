import uuid
from datetime import date, time, datetime, timezone
from decimal import Decimal
import pytest
from sqlalchemy.exc import IntegrityError

from app.models.organization import Organization, Branch, OrgStatus, BranchStatus
from app.models.user import User, UserRole, KYCStatus
from app.models.chit_scheme import ChitScheme
from app.models.chit_group import ChitGroup, ChitGroupStatus
from app.models.membership import ChitMembership, MembershipStatus
from app.models.auction import Auction, Bid, AuctionStatus
from app.models.installment import Installment, InstallmentStatus
from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app.models.payout import Payout, Surety, PayoutStatus, SuretyType, SuretyStatus
from app.models.audit_log import AuditLog


def test_create_organization_and_branches(db_session):
    """Test creating an organization with multiple branches and relationship navigation."""
    org = Organization(
        name="Chitties Kerala Pvt Ltd",
        registration_number="REG-KER-2026-001",
        tax_id="32AABCC1234F1Z1",
        status=OrgStatus.ACTIVE,
    )
    db_session.add(org)
    db_session.flush()

    branch1 = Branch(
        organization_id=org.id,
        branch_code="KOC-01",
        name="Kochi Main",
        address="MG Road, Kochi",
        phone="0484-2345678",
    )
    branch2 = Branch(
        organization_id=org.id,
        branch_code="TVM-01",
        name="Trivandrum City",
        address="Statue Junction, Trivandrum",
        phone="0471-2345678",
    )
    db_session.add_all([branch1, branch2])
    db_session.flush()

    assert org.id is not None
    assert len(org.branches) == 2
    assert branch1.organization.name == "Chitties Kerala Pvt Ltd"


def test_unique_branch_code_per_organization(db_session):
    """Verify branch_code must be unique within the same organization."""
    org = Organization(
        name="Apex Chits Ltd",
        registration_number=f"REG-APEX-{uuid.uuid4().hex[:6]}",
    )
    db_session.add(org)
    db_session.flush()

    b1 = Branch(organization_id=org.id, branch_code="BR-01", name="Branch One")
    db_session.add(b1)
    db_session.flush()

    # Attempt duplicate branch_code under same org
    b2 = Branch(organization_id=org.id, branch_code="BR-01", name="Duplicate Code Branch")
    db_session.add(b2)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_user_roles_and_kyc(db_session):
    """Test creating users across all 5 roles and KYC states."""
    org = Organization(
        name="Global Chits Co",
        registration_number=f"REG-GLO-{uuid.uuid4().hex[:6]}",
    )
    db_session.add(org)
    db_session.flush()

    branch = Branch(organization_id=org.id, branch_code="HQ-01", name="Headquarters")
    db_session.add(branch)
    db_session.flush()

    # 1. SuperAdmin (no org_id, no branch_id)
    super_admin = User(
        full_name="Platform Admin",
        email=f"super_{uuid.uuid4().hex[:6]}@chitties.io",
        phone="+919876543210",
        password_hash="hashed_pw_dummy",
        role=UserRole.SUPER_ADMIN,
        kyc_status=KYCStatus.VERIFIED,
    )

    # 2. Org Admin
    org_admin = User(
        organization_id=org.id,
        full_name="Foreman Officer",
        email=f"foreman_{uuid.uuid4().hex[:6]}@chitties.io",
        phone="+919876543211",
        password_hash="hashed_pw_dummy",
        role=UserRole.ORG_ADMIN,
        kyc_status=KYCStatus.VERIFIED,
    )

    # 3. Branch Manager
    branch_mgr = User(
        organization_id=org.id,
        branch_id=branch.id,
        full_name="Branch Head",
        email=f"bm_{uuid.uuid4().hex[:6]}@chitties.io",
        phone="+919876543212",
        password_hash="hashed_pw_dummy",
        role=UserRole.BRANCH_MANAGER,
        kyc_status=KYCStatus.VERIFIED,
    )

    # 4. Collection Agent
    agent = User(
        organization_id=org.id,
        branch_id=branch.id,
        full_name="Field Officer",
        email=f"agent_{uuid.uuid4().hex[:6]}@chitties.io",
        phone="+919876543213",
        password_hash="hashed_pw_dummy",
        role=UserRole.COLLECTION_AGENT,
        kyc_status=KYCStatus.VERIFIED,
    )

    # 5. Subscriber
    subscriber = User(
        organization_id=org.id,
        branch_id=branch.id,
        full_name="Alice Subscriber",
        email=f"alice_{uuid.uuid4().hex[:6]}@chitties.io",
        phone="+919876543214",
        password_hash="hashed_pw_dummy",
        role=UserRole.SUBSCRIBER,
        kyc_status=KYCStatus.PENDING,
    )

    db_session.add_all([super_admin, org_admin, branch_mgr, agent, subscriber])
    db_session.flush()

    assert super_admin.organization_id is None
    assert subscriber.role == UserRole.SUBSCRIBER
    assert subscriber.kyc_status == KYCStatus.PENDING


def test_user_unique_email(db_session):
    """Verify email uniqueness constraint is enforced globally."""
    email = f"duplicate_{uuid.uuid4().hex[:6]}@example.com"
    u1 = User(
        full_name="User One",
        email=email,
        phone="+919000000001",
        password_hash="pw1",
        role=UserRole.SUBSCRIBER,
    )
    db_session.add(u1)
    db_session.flush()

    u2 = User(
        full_name="User Two",
        email=email,
        phone="+919000000002",
        password_hash="pw2",
        role=UserRole.SUBSCRIBER,
    )
    db_session.add(u2)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_chit_scheme_check_constraints(db_session):
    """Test ChitScheme creation and validation of financial check constraints."""
    org = Organization(
        name="Scheme Test Org",
        registration_number=f"REG-SCH-{uuid.uuid4().hex[:6]}",
    )
    db_session.add(org)
    db_session.flush()

    # Valid scheme
    valid_scheme = ChitScheme(
        organization_id=org.id,
        name="Silver 1 Lakh 20 Months",
        total_value=Decimal("100000.00"),
        duration_months=20,
        monthly_installment=Decimal("5000.00"),
        foreman_commission_pct=Decimal("5.00"),
        max_bid_discount_pct=Decimal("30.00"),
        min_bid_discount_pct=Decimal("5.00"),
        foreman_month_one_reserved=True,
    )
    db_session.add(valid_scheme)
    db_session.flush()
    assert valid_scheme.id is not None

    # Invalid: negative total_value violates check constraint
    invalid_scheme = ChitScheme(
        organization_id=org.id,
        name="Invalid Scheme",
        total_value=Decimal("-5000.00"),
        duration_months=10,
        monthly_installment=Decimal("500.00"),
    )
    db_session.add(invalid_scheme)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_chit_group_calendar_constraints(db_session):
    """Test ChitGroup check constraint rejects auction day > 28."""
    org = Organization(
        name="Calendar Test Org",
        registration_number=f"REG-CAL-{uuid.uuid4().hex[:6]}",
    )
    db_session.add(org)
    db_session.flush()

    branch = Branch(organization_id=org.id, branch_code="B1", name="B1")
    db_session.add(branch)
    db_session.flush()

    scheme = ChitScheme(
        organization_id=org.id,
        name="Test Scheme",
        total_value=Decimal("50000.00"),
        duration_months=10,
        monthly_installment=Decimal("5000.00"),
    )
    db_session.add(scheme)
    db_session.flush()

    # Invalid: auction_day_of_month = 31 (violates <= 28 constraint to protect Feb)
    invalid_group = ChitGroup(
        organization_id=org.id,
        branch_id=branch.id,
        scheme_id=scheme.id,
        group_code="GRP-INVALID-31",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 10, 1),
        auction_day_of_month=31,
        auction_time=time(17, 0),
    )
    db_session.add(invalid_group)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_strictly_single_ticket_per_user(db_session):
    """
    CRITICAL USER DECISION TEST:
    Enforce strictly 1 ticket per user per chit group via uq_memberships_group_user.
    """
    org = Organization(
        name="Single Ticket Org",
        registration_number=f"REG-STK-{uuid.uuid4().hex[:6]}",
    )
    db_session.add(org)
    db_session.flush()

    branch = Branch(organization_id=org.id, branch_code="ST-01", name="Branch ST")
    scheme = ChitScheme(
        organization_id=org.id,
        name="Scheme ST",
        total_value=Decimal("50000.00"),
        duration_months=5,
        monthly_installment=Decimal("10000.00"),
    )
    db_session.add_all([branch, scheme])
    db_session.flush()

    group = ChitGroup(
        organization_id=org.id,
        branch_id=branch.id,
        scheme_id=scheme.id,
        group_code="GRP-ST-01",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 5, 1),
        auction_day_of_month=15,
        auction_time=time(15, 0),
    )
    user = User(
        organization_id=org.id,
        full_name="Bob SingleTicket",
        email=f"bob_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919111111111",
        password_hash="pw",
        role=UserRole.SUBSCRIBER,
    )
    db_session.add_all([group, user])
    db_session.flush()

    # Ticket 1 for Bob
    m1 = ChitMembership(chit_group_id=group.id, user_id=user.id, ticket_number=1)
    db_session.add(m1)
    db_session.flush()

    # Attempt to enroll Bob for a second ticket (Ticket 2) in the SAME group
    m2 = ChitMembership(chit_group_id=group.id, user_id=user.id, ticket_number=2)
    db_session.add(m2)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_unique_ticket_number_per_group(db_session):
    """Verify that two distinct members cannot be allocated the same ticket number."""
    org = Organization(
        name="Ticket Num Org",
        registration_number=f"REG-TNO-{uuid.uuid4().hex[:6]}",
    )
    db_session.add(org)
    db_session.flush()

    branch = Branch(organization_id=org.id, branch_code="TN-01", name="Branch TN")
    scheme = ChitScheme(
        organization_id=org.id,
        name="Scheme TN",
        total_value=Decimal("50000.00"),
        duration_months=5,
        monthly_installment=Decimal("10000.00"),
    )
    db_session.add_all([branch, scheme])
    db_session.flush()

    group = ChitGroup(
        organization_id=org.id,
        branch_id=branch.id,
        scheme_id=scheme.id,
        group_code="GRP-TN-01",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 5, 1),
        auction_day_of_month=15,
        auction_time=time(15, 0),
    )
    user1 = User(
        organization_id=org.id,
        full_name="User One",
        email=f"u1_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919222222221",
        password_hash="pw",
        role=UserRole.SUBSCRIBER,
    )
    user2 = User(
        organization_id=org.id,
        full_name="User Two",
        email=f"u2_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919222222222",
        password_hash="pw",
        role=UserRole.SUBSCRIBER,
    )
    db_session.add_all([group, user1, user2])
    db_session.flush()

    # User 1 gets Ticket #1
    m1 = ChitMembership(chit_group_id=group.id, user_id=user1.id, ticket_number=1)
    db_session.add(m1)
    db_session.flush()

    # User 2 also tries to get Ticket #1
    m2 = ChitMembership(chit_group_id=group.id, user_id=user2.id, ticket_number=1)
    db_session.add(m2)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_auction_and_bids_fcfs_order(db_session):
    """
    Test auction and bids First-Come, First-Served tie-breaking queries.
    When discounts are equal, the earlier timestamp must be ranked first.
    """
    org = Organization(
        name="Auction FCFS Org",
        registration_number=f"REG-AUC-{uuid.uuid4().hex[:6]}",
    )
    db_session.add(org)
    db_session.flush()

    branch = Branch(organization_id=org.id, branch_code="A-01", name="Branch A")
    scheme = ChitScheme(
        organization_id=org.id,
        name="Scheme AUC",
        total_value=Decimal("100000.00"),
        duration_months=10,
        monthly_installment=Decimal("10000.00"),
    )
    db_session.add_all([branch, scheme])
    db_session.flush()

    group = ChitGroup(
        organization_id=org.id,
        branch_id=branch.id,
        scheme_id=scheme.id,
        group_code="GRP-AUC-01",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 10, 1),
        auction_day_of_month=15,
        auction_time=time(17, 0),
    )
    u1 = User(
        organization_id=org.id,
        full_name="Bidder 1",
        email=f"b1_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919333333331",
        password_hash="pw",
        role=UserRole.SUBSCRIBER,
    )
    u2 = User(
        organization_id=org.id,
        full_name="Bidder 2",
        email=f"b2_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919333333332",
        password_hash="pw",
        role=UserRole.SUBSCRIBER,
    )
    db_session.add_all([group, u1, u2])
    db_session.flush()

    m1 = ChitMembership(chit_group_id=group.id, user_id=u1.id, ticket_number=1)
    m2 = ChitMembership(chit_group_id=group.id, user_id=u2.id, ticket_number=2)
    db_session.add_all([m1, m2])
    db_session.flush()

    auction = Auction(
        chit_group_id=group.id,
        month_number=2,
        scheduled_at=datetime.now(timezone.utc),
        status=AuctionStatus.OPEN,
    )
    db_session.add(auction)
    db_session.flush()

    # Bidder 1 bids max discount 30,000 at T1
    bid1 = Bid(
        auction_id=auction.id,
        chit_membership_id=m1.id,
        bid_discount_amount=Decimal("30000.00"),
        timestamp=datetime(2026, 2, 15, 17, 0, 1, tzinfo=timezone.utc),
    )
    # Bidder 2 also bids max discount 30,000 at T2 (2 seconds later)
    bid2 = Bid(
        auction_id=auction.id,
        chit_membership_id=m2.id,
        bid_discount_amount=Decimal("30000.00"),
        timestamp=datetime(2026, 2, 15, 17, 0, 3, tzinfo=timezone.utc),
    )
    db_session.add_all([bid1, bid2])
    db_session.flush()

    # Query highest discount, ordered by earliest timestamp (FCFS rule)
    winning_bid = (
        db_session.query(Bid)
        .filter(Bid.auction_id == auction.id, Bid.is_valid.is_(True))
        .order_by(Bid.bid_discount_amount.desc(), Bid.timestamp.asc())
        .first()
    )

    assert winning_bid.id == bid1.id
    assert winning_bid.chit_membership_id == m1.id


def test_payment_idempotency_and_ledger(db_session):
    """Verify that duplicate transaction_reference or receipt_number is rejected."""
    org = Organization(
        name="Payment Test Org",
        registration_number=f"REG-PAY-{uuid.uuid4().hex[:6]}",
    )
    db_session.add(org)
    db_session.flush()

    branch = Branch(organization_id=org.id, branch_code="P-01", name="Branch P")
    scheme = ChitScheme(
        organization_id=org.id,
        name="Scheme P",
        total_value=Decimal("50000.00"),
        duration_months=5,
        monthly_installment=Decimal("10000.00"),
    )
    db_session.add_all([branch, scheme])
    db_session.flush()

    group = ChitGroup(
        organization_id=org.id,
        branch_id=branch.id,
        scheme_id=scheme.id,
        group_code="GRP-PAY-01",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 5, 1),
        auction_day_of_month=15,
        auction_time=time(17, 0),
    )
    agent = User(
        organization_id=org.id,
        branch_id=branch.id,
        full_name="Agent Cashier",
        email=f"cashier_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919444444441",
        password_hash="pw",
        role=UserRole.COLLECTION_AGENT,
    )
    sub = User(
        organization_id=org.id,
        branch_id=branch.id,
        full_name="Customer Charlie",
        email=f"charlie_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919444444442",
        password_hash="pw",
        role=UserRole.SUBSCRIBER,
    )
    db_session.add_all([group, agent, sub])
    db_session.flush()

    m = ChitMembership(chit_group_id=group.id, user_id=sub.id, ticket_number=1)
    db_session.add(m)
    db_session.flush()

    inst = Installment(
        chit_group_id=group.id,
        chit_membership_id=m.id,
        month_number=1,
        due_date=date(2026, 1, 15),
        gross_amount=Decimal("10000.00"),
        dividend_amount=Decimal("0.00"),
        net_due_amount=Decimal("10000.00"),
        status=InstallmentStatus.UNPAID,
    )
    db_session.add(inst)
    db_session.flush()

    # Initial successful payment
    tx_ref = f"TXN-UPI-{uuid.uuid4().hex[:8]}"
    receipt = f"REC-2026-{uuid.uuid4().hex[:6]}"
    p1 = Payment(
        organization_id=org.id,
        chit_membership_id=m.id,
        installment_id=inst.id,
        amount_paid=Decimal("10000.00"),
        payment_method=PaymentMethod.UPI,
        transaction_reference=tx_ref,
        receipt_number=receipt,
        recorded_by_user_id=agent.id,
        status=PaymentStatus.COMPLETED,
    )
    db_session.add(p1)
    db_session.flush()
    assert p1.id is not None

    # Duplicate payment submission with exact same transaction_reference
    p2 = Payment(
        organization_id=org.id,
        chit_membership_id=m.id,
        installment_id=inst.id,
        amount_paid=Decimal("10000.00"),
        payment_method=PaymentMethod.UPI,
        transaction_reference=tx_ref,
        receipt_number=f"REC-NEW-{uuid.uuid4().hex[:6]}",
        recorded_by_user_id=agent.id,
    )
    db_session.add(p2)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_payout_and_surety_workflow(db_session):
    """Test two-step prize verification: PENDING_SURETY and adding Sureties."""
    org = Organization(
        name="Payout Workflow Org",
        registration_number=f"REG-POW-{uuid.uuid4().hex[:6]}",
    )
    db_session.add(org)
    db_session.flush()

    branch = Branch(organization_id=org.id, branch_code="W-01", name="Branch W")
    scheme = ChitScheme(
        organization_id=org.id,
        name="Scheme W",
        total_value=Decimal("500000.00"),
        duration_months=50,
        monthly_installment=Decimal("10000.00"),
    )
    db_session.add_all([branch, scheme])
    db_session.flush()

    group = ChitGroup(
        organization_id=org.id,
        branch_id=branch.id,
        scheme_id=scheme.id,
        group_code="GRP-W-01",
        start_date=date(2026, 1, 1),
        end_date=date(2030, 2, 1),
        auction_day_of_month=15,
        auction_time=time(17, 0),
    )
    bm = User(
        organization_id=org.id,
        branch_id=branch.id,
        full_name="Manager Mike",
        email=f"bm_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919555555551",
        password_hash="pw",
        role=UserRole.BRANCH_MANAGER,
    )
    winner = User(
        organization_id=org.id,
        branch_id=branch.id,
        full_name="Winner Wendy",
        email=f"wendy_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919555555552",
        password_hash="pw",
        role=UserRole.SUBSCRIBER,
    )
    db_session.add_all([group, bm, winner])
    db_session.flush()

    m = ChitMembership(
        chit_group_id=group.id,
        user_id=winner.id,
        ticket_number=7,
        status=MembershipStatus.PRIZED,
    )
    db_session.add(m)
    db_session.flush()

    auction = Auction(
        chit_group_id=group.id,
        month_number=5,
        scheduled_at=datetime.now(timezone.utc),
        status=AuctionStatus.FINALIZED,
        winning_membership_id=m.id,
        winning_bid_discount=Decimal("120000.00"),
        foreman_commission=Decimal("25000.00"),
        total_dividend_pool=Decimal("95000.00"),
        dividend_per_ticket=Decimal("1900.00"),
        net_payable_installment=Decimal("8100.00"),
    )
    db_session.add(auction)
    db_session.flush()

    # Step 1: Payout created in PENDING_SURETY status
    payout = Payout(
        auction_id=auction.id,
        chit_membership_id=m.id,
        gross_prize_amount=Decimal("380000.00"),
        foreman_charges_deducted=Decimal("0.00"),
        arrears_deducted=Decimal("0.00"),
        net_disbursed_amount=Decimal("380000.00"),
        disbursement_status=PayoutStatus.PENDING_SURETY,
    )
    db_session.add(payout)
    db_session.flush()
    assert payout.disbursement_status == PayoutStatus.PENDING_SURETY

    # Step 2: Prized subscriber submits Guarantor surety
    surety = Surety(
        payout_id=payout.id,
        surety_type=SuretyType.GUARANTOR,
        guarantor_name="George Guarantor",
        guarantor_phone="+919555555599",
        document_reference="DOCS/SURETY/2026/G_GEORGE.pdf",
        verification_status=SuretyStatus.VERIFIED,
        verified_by_user_id=bm.id,
        remarks="Verified government employee salary certificate and KYC.",
    )
    db_session.add(surety)
    db_session.flush()

    # Payout updated to SURETY_APPROVED
    payout.disbursement_status = PayoutStatus.SURETY_APPROVED
    db_session.flush()

    assert len(payout.sureties) == 1
    assert payout.sureties[0].guarantor_name == "George Guarantor"
    assert payout.disbursement_status == PayoutStatus.SURETY_APPROVED


def test_audit_log_mutation(db_session):
    """Test creating an immutable audit log record with JSON mutation diff."""
    org = Organization(
        name="Audit Test Org",
        registration_number=f"REG-AUD-{uuid.uuid4().hex[:6]}",
    )
    db_session.add(org)
    db_session.flush()

    user = User(
        organization_id=org.id,
        full_name="Admin Audit",
        email=f"audit_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919666666661",
        password_hash="pw",
        role=UserRole.ORG_ADMIN,
    )
    db_session.add(user)
    db_session.flush()

    audit = AuditLog(
        organization_id=org.id,
        user_id=user.id,
        action="AUCTION_FINALIZED",
        entity_type="auctions",
        entity_id=uuid.uuid4(),
        changes_json={
            "month_number": 3,
            "winning_bid_discount": "100000.00",
            "dividend_per_ticket": "1500.00",
        },
        ip_address="192.168.1.100",
    )
    db_session.add(audit)
    db_session.flush()

    assert audit.id is not None
    assert audit.changes_json["month_number"] == 3
    assert audit.action == "AUCTION_FINALIZED"
