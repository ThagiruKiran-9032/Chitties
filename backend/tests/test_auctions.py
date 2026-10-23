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


def setup_active_chit_group(db_session, num_members=5):
    """Helper fixture to create an active group with enrolled subscribers, scheme, and month 1 auction."""
    org = Organization(name="Auction Test Org", registration_number=f"REG-AUC-{uuid.uuid4().hex[:6]}")
    db_session.add(org)
    db_session.commit()

    branch = Branch(organization_id=org.id, name="Auction Branch", branch_code=f"BR-{uuid.uuid4().hex[:4]}")
    db_session.add(branch)
    db_session.commit()

    admin = User(
        organization_id=org.id,
        branch_id=branch.id,
        full_name="Auction Manager",
        email=f"mgr_{uuid.uuid4().hex[:6]}@example.com",
        phone="+919800000010",
        password_hash=get_password_hash("password123"),
        role=UserRole.BRANCH_MANAGER,
        kyc_status=KYCStatus.VERIFIED,
    )
    db_session.add(admin)
    db_session.commit()

    scheme = ChitScheme(
        organization_id=org.id,
        name="100K 5M Scheme",
        total_value=Decimal("100000.00"),
        duration_months=num_members,
        monthly_installment=Decimal("20000.00"),
        foreman_commission_pct=Decimal("5.00"),
        min_bid_discount_pct=Decimal("5.00"),     # Floor: ₹5,000
        max_bid_discount_pct=Decimal("30.00"),    # Cap: ₹30,000
        foreman_month_one_reserved=False,        # Open round 1 to subscriber bidding for testing
        is_active=True,
    )
    db_session.add(scheme)
    db_session.commit()

    group = ChitGroup(
        organization_id=org.id,
        branch_id=branch.id,
        scheme_id=scheme.id,
        manager_id=admin.id,
        group_code=f"GRP-AUC-{uuid.uuid4().hex[:4]}",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 9, 30),
        current_month=1,
        auction_day_of_month=15,
        auction_time=time(16, 0),
        status=ChitGroupStatus.ACTIVE,
    )
    db_session.add(group)
    db_session.commit()

    members = []
    for i in range(1, num_members + 1):
        sub_user = User(
            organization_id=org.id,
            branch_id=branch.id,
            full_name=f"Subscriber {i}",
            email=f"sub_{i}_{uuid.uuid4().hex[:6]}@example.com",
            phone=f"+9198000000{i:02d}",
            password_hash=get_password_hash("password123"),
            role=UserRole.SUBSCRIBER,
            kyc_status=KYCStatus.VERIFIED,
        )
        db_session.add(sub_user)
        db_session.commit()

        membership = ChitMembership(
            chit_group_id=group.id,
            user_id=sub_user.id,
            ticket_number=i,
            status=MembershipStatus.ACTIVE,
        )
        db_session.add(membership)
        db_session.commit()

        # Month 1 installment
        inst = Installment(
            chit_group_id=group.id,
            chit_membership_id=membership.id,
            month_number=1,
            due_date=date(2026, 5, 1),
            gross_amount=Decimal("20000.00"),
            dividend_amount=Decimal("0.00"),
            penalty_amount=Decimal("0.00"),
            net_due_amount=Decimal("20000.00"),
            paid_amount=Decimal("0.00"),
            status=InstallmentStatus.UNPAID,
        )
        db_session.add(inst)
        members.append((sub_user, membership))

    # Month 1 Auction
    auction = Auction(
        chit_group_id=group.id,
        month_number=1,
        scheduled_at=datetime(2026, 5, 15, 16, 0, tzinfo=timezone.utc),
        status=AuctionStatus.SCHEDULED,
        is_foreman_month=False,
    )
    db_session.add(auction)
    db_session.commit()

    return {
        "org": org,
        "branch": branch,
        "admin": admin,
        "scheme": scheme,
        "group": group,
        "members": members,
        "auction": auction,
    }


def test_get_group_auctions_and_detail(client, db_session, auth_headers):
    """Verify listing and deep detail inspection for chit group auctions."""
    data = setup_active_chit_group(db_session)
    admin = data["admin"]
    group = data["group"]
    auction = data["auction"]
    sub1, mem1 = data["members"][0]

    # List auctions for group
    resp = client.get(f"/api/v1/auctions/group/{group.id}", headers=auth_headers(admin))
    assert resp.status_code == status.HTTP_200_OK
    auctions = resp.json()
    assert len(auctions) == 1
    assert auctions[0]["month_number"] == 1
    assert auctions[0]["status"] == "SCHEDULED"

    # Subscriber fetches auction detail
    resp_detail = client.get(f"/api/v1/auctions/{auction.id}", headers=auth_headers(sub1))
    assert resp_detail.status_code == status.HTTP_200_OK
    detail = resp_detail.json()
    assert detail["group_code"] == group.group_code
    assert float(detail["min_bid_discount"]) == 5000.00   # 5% of 100K
    assert float(detail["max_bid_discount"]) == 30000.00  # 30% of 100K
    assert detail["user_ticket_number"] == 1
    assert detail["user_is_prized"] is False


def test_start_auction_lifecycle(client, db_session, auth_headers):
    """Branch Manager opens an auction; subscriber cannot start it."""
    data = setup_active_chit_group(db_session)
    admin = data["admin"]
    sub1, _ = data["members"][0]
    auction = data["auction"]

    # Subscriber forbidden from starting
    resp_sub = client.post(f"/api/v1/auctions/{auction.id}/start", headers=auth_headers(sub1))
    assert resp_sub.status_code == status.HTTP_403_FORBIDDEN

    # Manager starts auction
    resp_start = client.post(f"/api/v1/auctions/{auction.id}/start", headers=auth_headers(admin))
    assert resp_start.status_code == status.HTTP_200_OK
    assert resp_start.json()["status"] == "OPEN"

    # Confirm auction status in DB
    db_session.refresh(auction)
    assert auction.status == AuctionStatus.OPEN
    assert auction.opened_at is not None


def test_bidding_bounds_and_validations(client, db_session, auth_headers):
    """Enforces minimum floor, maximum ceiling, and strict incremental increases."""
    data = setup_active_chit_group(db_session)
    admin = data["admin"]
    sub1, _ = data["members"][0]
    sub2, _ = data["members"][1]
    auction = data["auction"]

    # Open auction
    client.post(f"/api/v1/auctions/{auction.id}/start", headers=auth_headers(admin))

    # Bid below floor (₹4,000 < ₹5,000 floor)
    resp_below = client.post(
        f"/api/v1/auctions/{auction.id}/bids",
        json={"bid_discount_amount": 4000.00},
        headers=auth_headers(sub1),
    )
    assert resp_below.status_code == status.HTTP_400_BAD_REQUEST
    assert "below the minimum allowed floor" in resp_below.json()["detail"]

    # Bid above statutory cap (₹35,000 > ₹30,000 cap)
    resp_above = client.post(
        f"/api/v1/auctions/{auction.id}/bids",
        json={"bid_discount_amount": 35000.00},
        headers=auth_headers(sub1),
    )
    assert resp_above.status_code == status.HTTP_400_BAD_REQUEST
    assert "exceeds the maximum statutory cap" in resp_above.json()["detail"]

    # Valid first bid: ₹10,000
    resp_bid1 = client.post(
        f"/api/v1/auctions/{auction.id}/bids",
        json={"bid_discount_amount": 10000.00},
        headers=auth_headers(sub1),
    )
    assert resp_bid1.status_code == status.HTTP_201_CREATED
    assert resp_bid1.json()["ticket_number"] == 1
    assert float(resp_bid1.json()["bid_discount_amount"]) == 10000.00

    # Sub 2 bids lower than or equal to current highest (₹9,000 or ₹10,000)
    resp_lower = client.post(
        f"/api/v1/auctions/{auction.id}/bids",
        json={"bid_discount_amount": 9000.00},
        headers=auth_headers(sub2),
    )
    assert resp_lower.status_code == status.HTTP_400_BAD_REQUEST
    assert "strictly exceed current highest bid" in resp_lower.json()["detail"]

    # Sub 2 bids higher: ₹15,000
    resp_bid2 = client.post(
        f"/api/v1/auctions/{auction.id}/bids",
        json={"bid_discount_amount": 15000.00},
        headers=auth_headers(sub2),
    )
    assert resp_bid2.status_code == status.HTTP_201_CREATED
    assert resp_bid2.json()["ticket_number"] == 2


def test_fcfs_ceiling_cap_rule(client, db_session, auth_headers):
    """First subscriber to bid the ceiling cap wins; subsequent ceiling bids are rejected under FCFS."""
    data = setup_active_chit_group(db_session)
    admin = data["admin"]
    sub1, _ = data["members"][0]
    sub2, _ = data["members"][1]
    auction = data["auction"]

    client.post(f"/api/v1/auctions/{auction.id}/start", headers=auth_headers(admin))

    # Sub 1 hits the ceiling cap of ₹30,000
    resp_cap1 = client.post(
        f"/api/v1/auctions/{auction.id}/bids",
        json={"bid_discount_amount": 30000.00},
        headers=auth_headers(sub1),
    )
    assert resp_cap1.status_code == status.HTTP_201_CREATED

    # Sub 2 attempts to also bid ₹30,000
    resp_cap2 = client.post(
        f"/api/v1/auctions/{auction.id}/bids",
        json={"bid_discount_amount": 30000.00},
        headers=auth_headers(sub2),
    )
    assert resp_cap2.status_code == status.HTTP_400_BAD_REQUEST
    assert "already been claimed" in resp_cap2.json()["detail"]
    assert "FCFS" in resp_cap2.json()["detail"]


def test_close_auction_and_dividend_ledger_distribution(client, db_session, auth_headers):
    """
    Closing auction calculates exact prize money, foreman commission, dividend per ticket,
    marks winner as PRIZED, and updates month 2 installments with dividend deductions.
    """
    data = setup_active_chit_group(db_session)
    admin = data["admin"]
    sub1, mem1 = data["members"][0]
    auction = data["auction"]
    group = data["group"]

    # Open auction
    client.post(f"/api/v1/auctions/{auction.id}/start", headers=auth_headers(admin))

    # Sub 1 places winning bid of ₹20,000
    client.post(
        f"/api/v1/auctions/{auction.id}/bids",
        json={"bid_discount_amount": 20000.00},
        headers=auth_headers(sub1),
    )

    # Admin closes auction
    resp_close = client.post(f"/api/v1/auctions/{auction.id}/close", headers=auth_headers(admin))
    assert resp_close.status_code == status.HTTP_200_OK
    settlement = resp_close.json()

    # Math Verification:
    # Total Value = ₹100,000. Winning Discount = ₹20,000.
    # Prize Money = 100,000 - 20,000 = 80,000.
    # Foreman Commission = 5% of 100,000 = 5,000.
    # Dividend Pool = 20,000 - 5,000 = 15,000.
    # Total Members = 5.
    # Dividend Per Member = 15,000 / 5 = 3,000.
    # Next Month Net Installment = 20,000 - 3,000 = 17,000.
    assert float(settlement["winning_bid_discount"]) == 20000.00
    assert float(settlement["prize_amount"]) == 80000.00
    assert float(settlement["foreman_commission"]) == 5000.00
    assert float(settlement["total_dividend_pool"]) == 15000.00
    assert float(settlement["dividend_per_ticket"]) == 3000.00
    assert float(settlement["net_payable_installment"]) == 17000.00
    assert settlement["winner_ticket_number"] == 1
    assert settlement["next_month_installments_generated"] == 5

    # Member 1 should now be PRIZED
    db_session.refresh(mem1)
    assert mem1.status == MembershipStatus.PRIZED

    # Verify Month 2 installments generated for all members with dividend applied
    m2_installments = db_session.query(Installment).filter(
        Installment.chit_group_id == group.id,
        Installment.month_number == 2,
    ).all()
    assert len(m2_installments) == 5
    for inst in m2_installments:
        assert inst.gross_amount == Decimal("20000.00")
        assert inst.dividend_amount == Decimal("3000.00")
        assert inst.net_due_amount == Decimal("17000.00")
        assert inst.status == InstallmentStatus.UNPAID

    # Verify Month 2 auction was scheduled
    m2_auction = db_session.query(Auction).filter(
        Auction.chit_group_id == group.id,
        Auction.month_number == 2,
    ).first()
    assert m2_auction is not None
    assert m2_auction.status == AuctionStatus.SCHEDULED


def test_prized_member_cannot_bid_in_subsequent_rounds(client, db_session, auth_headers):
    """Subscribers who have already won a prize are strictly blocked from placing bids in future rounds."""
    data = setup_active_chit_group(db_session)
    admin = data["admin"]
    sub1, mem1 = data["members"][0]
    sub2, mem2 = data["members"][1]
    auction = data["auction"]
    group = data["group"]

    # Month 1 auction
    client.post(f"/api/v1/auctions/{auction.id}/start", headers=auth_headers(admin))
    client.post(f"/api/v1/auctions/{auction.id}/bids", json={"bid_discount_amount": 10000.00}, headers=auth_headers(sub1))
    client.post(f"/api/v1/auctions/{auction.id}/close", headers=auth_headers(admin))

    # Retrieve Month 2 auction
    m2_auction = db_session.query(Auction).filter(
        Auction.chit_group_id == group.id,
        Auction.month_number == 2,
    ).first()
    assert m2_auction is not None

    # Open Month 2 auction
    client.post(f"/api/v1/auctions/{m2_auction.id}/start", headers=auth_headers(admin))

    # Prized Sub 1 attempts to bid in Month 2
    resp_prized_bid = client.post(
        f"/api/v1/auctions/{m2_auction.id}/bids",
        json={"bid_discount_amount": 12000.00},
        headers=auth_headers(sub1),
    )
    assert resp_prized_bid.status_code == status.HTTP_400_BAD_REQUEST
    assert "already prized and cannot bid" in resp_prized_bid.json()["detail"]

    # Unprized Sub 2 bids successfully
    resp_unprized = client.post(
        f"/api/v1/auctions/{m2_auction.id}/bids",
        json={"bid_discount_amount": 12000.00},
        headers=auth_headers(sub2),
    )
    assert resp_unprized.status_code == status.HTTP_201_CREATED
    assert resp_unprized.json()["ticket_number"] == 2


def test_websocket_live_auction_channel(client, db_session):
    """Connects to auction WebSocket, exchanges PING/PONG and verifies real-time connection."""
    data = setup_active_chit_group(db_session)
    admin = data["admin"]
    auction = data["auction"]

    token = create_access_token({
        "sub": str(admin.id),
        "role": admin.role.value,
        "org_id": str(admin.organization_id),
    })

    # Test live WebSocket connection
    with client.websocket_connect(f"/api/v1/auctions/ws/{auction.id}?token={token}") as ws:
        ws.send_json({"type": "PING"})
        reply = ws.receive_json()
        assert reply["type"] == "PONG"
