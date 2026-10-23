import json
import logging
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


def json_serializer(obj):
    """Custom serializer for Decimal, UUID, and datetime objects."""
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


class AuctionConnectionManager:
    """
    Manages real-time WebSocket connections per live auction room.
    Provides room-isolated broadcasting for bids, timer events, and winner celebrations.
    """

    def __init__(self):
        # Maps auction_id -> Set of active WebSocket instances
        self._rooms: Dict[uuid.UUID, Set[WebSocket]] = {}

    async def connect(self, auction_id: uuid.UUID, websocket: WebSocket):
        await websocket.accept()
        if auction_id not in self._rooms:
            self._rooms[auction_id] = set()
        self._rooms[auction_id].add(websocket)
        logger.info(f"WebSocket client connected to auction {auction_id}. Total in room: {len(self._rooms[auction_id])}")

    def disconnect(self, auction_id: uuid.UUID, websocket: WebSocket):
        if auction_id in self._rooms and websocket in self._rooms[auction_id]:
            self._rooms[auction_id].remove(websocket)
            logger.info(f"WebSocket client left auction {auction_id}. Remaining: {len(self._rooms[auction_id])}")
            if not self._rooms[auction_id]:
                del self._rooms[auction_id]

    async def broadcast(self, auction_id: uuid.UUID, message: dict):
        """Broadcasts a structured JSON message to all subscribers in the room."""
        if auction_id not in self._rooms:
            return

        payload_str = json.dumps(message, default=json_serializer)
        dead_sockets = set()

        for ws in self._rooms[auction_id]:
            try:
                await ws.send_text(payload_str)
            except Exception as e:
                logger.warning(f"Failed sending to socket in auction {auction_id}: {e}")
                dead_sockets.add(ws)

        for dead_ws in dead_sockets:
            self._rooms[auction_id].discard(dead_ws)


# Global singleton instance
auction_ws_manager = AuctionConnectionManager()
