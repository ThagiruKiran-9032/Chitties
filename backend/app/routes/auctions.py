import uuid
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_roles, require_permission
from app.services.authz_service import Permission
from app.models.auction import Bid
from app.models.user import User, UserRole
from app.schemas.auction import (
    AuctionCloseResponse,
    AuctionDetailResponse,
    AuctionSummaryResponse,
    BidCreate,
    BidResponse,
)
from app.models.auction import AuctionStatus
from app.services.auction_service import AuctionService
from app.services.auction_ws_manager import auction_ws_manager

router = APIRouter(prefix="/auctions", tags=["Auctions & Bidding Engine"])


@router.get("", response_model=List[AuctionSummaryResponse])
def list_organization_auctions(
    status: Optional[AuctionStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all auctions across the organization, optionally filtered by status."""
    return AuctionService.list_organization_auctions(db, current_user, status)


@router.get("/group/{group_id}", response_model=List[AuctionSummaryResponse])
def get_group_auctions(
    group_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all monthly auction rounds scheduled or conducted for a specific Chit Group."""
    return AuctionService.get_group_auctions(db, group_id, current_user)


@router.get("/{auction_id}", response_model=AuctionDetailResponse)
def get_auction_detail(
    auction_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full details, discount parameters, user ticket context, and recent bids for an auction."""
    return AuctionService.get_auction_detail(db, auction_id, current_user)


@router.post("/{auction_id}/start")
async def start_auction(
    auction_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission(Permission.MANAGE_AUCTIONS)
    ),
):
    """
    Open an auction session for live bidding.
    Broadcasts the AUCTION_STARTED event to all connected WebSocket subscribers.
    """
    auction = await AuctionService.start_auction(db, auction_id, current_user)
    return {
        "message": f"Auction for Month {auction.month_number} is now OPEN.",
        "auction_id": str(auction.id),
        "status": auction.status.value,
        "opened_at": auction.opened_at.isoformat() if auction.opened_at else None,
    }


@router.post("/{auction_id}/bids", response_model=BidResponse, status_code=status.HTTP_201_CREATED)
async def place_bid(
    auction_id: uuid.UUID,
    payload: BidCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit a reverse discount bid.
    Enforces discount floor/cap, strict increment, and First-Come, First-Served (FCFS) ranking.
    """
    bid = await AuctionService.place_bid(
        db=db,
        auction_id=auction_id,
        bid_discount_amount=payload.bid_discount_amount,
        current_user=current_user,
        membership_id=payload.chit_membership_id,
    )
    return BidResponse(
        id=bid.id,
        auction_id=bid.auction_id,
        chit_membership_id=bid.chit_membership_id,
        ticket_number=bid.membership.ticket_number if bid.membership else None,
        bidder_name=bid.membership.user.full_name if (bid.membership and bid.membership.user) else None,
        bid_discount_amount=bid.bid_discount_amount,
        timestamp=bid.timestamp,
        is_valid=bid.is_valid,
    )


@router.get("/{auction_id}/bids", response_model=List[BidResponse])
def get_auction_bids(
    auction_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full chronological or ranked bid history for an auction."""
    # Enforce access check via detail call
    AuctionService.get_auction_detail(db, auction_id, current_user)

    bids = (
        db.query(Bid)
        .filter(Bid.auction_id == auction_id, Bid.is_valid == True)
        .order_by(Bid.bid_discount_amount.desc(), Bid.timestamp.asc())
        .all()
    )

    return [
        BidResponse(
            id=b.id,
            auction_id=b.auction_id,
            chit_membership_id=b.chit_membership_id,
            ticket_number=b.membership.ticket_number if b.membership else None,
            bidder_name=b.membership.user.full_name if (b.membership and b.membership.user) else None,
            bid_discount_amount=b.bid_discount_amount,
            timestamp=b.timestamp,
            is_valid=b.is_valid,
        )
        for b in bids
    ]


@router.post("/{auction_id}/close", response_model=AuctionCloseResponse)
async def close_auction(
    auction_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission(Permission.MANAGE_AUCTIONS)
    ),
):
    """
    Close and settle an auction round.
    Computes Foreman Commission, Dividend Pool, Dividend Per Ticket, marks the winner as PRIZED,
    and automatically adjusts/generates next month's installment ledger obligations.
    """
    return await AuctionService.close_auction(db, auction_id, current_user)


@router.websocket("/ws/{auction_id}")
async def auction_websocket_endpoint(
    websocket: WebSocket,
    auction_id: uuid.UUID,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Real-time bidirectional WebSocket channel for live auction bidding, timer sync, and winner announcements.
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        payload = decode_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        user_id = uuid.UUID(user_id_str)
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await auction_ws_manager.connect(auction_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "PING":
                await websocket.send_json({"type": "PONG"})
            elif msg_type == "BID":
                discount_raw = data.get("bid_discount_amount")
                if discount_raw is None:
                    await websocket.send_json({"type": "BID_REJECTED", "detail": "Missing bid_discount_amount"})
                    continue

                try:
                    discount_amount = Decimal(str(discount_raw))
                    membership_id = uuid.UUID(data["chit_membership_id"]) if data.get("chit_membership_id") else None

                    bid = await AuctionService.place_bid(
                        db=db,
                        auction_id=auction_id,
                        bid_discount_amount=discount_amount,
                        current_user=user,
                        membership_id=membership_id,
                    )
                    await websocket.send_json({
                        "type": "BID_ACCEPTED",
                        "bid_id": str(bid.id),
                        "amount": str(bid.bid_discount_amount),
                    })
                except HTTPException as he:
                    await websocket.send_json({"type": "BID_REJECTED", "detail": he.detail})
                except Exception as e:
                    await websocket.send_json({"type": "BID_REJECTED", "detail": str(e)})

    except WebSocketDisconnect:
        auction_ws_manager.disconnect(auction_id, websocket)
    except Exception:
        auction_ws_manager.disconnect(auction_id, websocket)
