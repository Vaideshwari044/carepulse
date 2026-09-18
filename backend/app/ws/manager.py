"""WebSocket connection manager for CarePulse real-time monitoring."""
from __future__ import annotations

import asyncio
import json
import uuid
from collections import OrderedDict
from datetime import UTC, datetime
from typing import Any, Optional

import structlog
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

logger = structlog.get_logger(__name__)

HEARTBEAT_INTERVAL = 20  # seconds
MAX_MISSED_HEARTBEATS = 2
MAX_CLIENTS = 500
MAX_QUEUE_SIZE = 100
DEDUP_HISTORY = 500


class ClientState:
    def __init__(self, websocket: WebSocket, user_id: str, role: str):
        self.websocket = websocket
        self.user_id = user_id
        self.role = role
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
        self.last_heartbeat = datetime.now(UTC)
        self.missed_heartbeats = 0
        self.connected = True
        self.seen_ids: OrderedDict = OrderedDict()  # LRU dedup


class ConnectionManager:
    def __init__(self):
        self._clients: OrderedDict[str, ClientState] = OrderedDict()
        self._lock = asyncio.Lock()
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: WebSocket, token: str) -> Optional[ClientState]:
        """Authenticate and register WebSocket client."""
        try:
            from app.core.security import decode_access_token
            from jose import JWTError
            payload = decode_access_token(token)
            user_id = payload.get("sub", "")
            role = payload.get("role", "clinician")
        except Exception:
            await websocket.close(code=4401)
            return None

        await websocket.accept()
        client = ClientState(websocket, user_id, role)

        async with self._lock:
            # LRU eviction if at max capacity
            while len(self._clients) >= MAX_CLIENTS:
                oldest_key = next(iter(self._clients))
                old_client = self._clients.pop(oldest_key)
                old_client.connected = False
                try:
                    await old_client.websocket.close()
                except Exception:
                    pass

            client_id = str(uuid.uuid4())
            self._clients[client_id] = client

        # Start heartbeat task if not running
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        logger.info("ws.connected", user_id=user_id, total_clients=len(self._clients))

        # Start sender for this client
        asyncio.create_task(self._sender_loop(client_id, client))

        return client

    async def disconnect(self, client: ClientState) -> None:
        client.connected = False
        async with self._lock:
            for k, v in list(self._clients.items()):
                if v is client:
                    del self._clients[k]
                    break
        try:
            await client.websocket.close()
        except Exception:
            pass

    async def broadcast(self, event_type: str, patient_code: str, payload: Any) -> None:
        """Broadcast event to all connected clients."""
        event_id = str(uuid.uuid4())
        envelope = {
            "event": event_type,
            "event_id": event_id,
            "emitted_at": datetime.now(UTC).isoformat(),
            "patient_code": patient_code,
            "payload": payload,
        }
        await self._send_to_all(envelope)

    async def broadcast_system(self, event_type: str, payload: Any) -> None:
        """Broadcast system event to all connected clients."""
        event_id = str(uuid.uuid4())
        envelope = {
            "event": event_type,
            "event_id": event_id,
            "emitted_at": datetime.now(UTC).isoformat(),
            "patient_code": None,
            "payload": payload,
        }
        await self._send_to_all(envelope)

    async def _send_to_all(self, envelope: dict) -> None:
        """Fan out message to all clients."""
        async with self._lock:
            clients = list(self._clients.items())

        dead = []
        for client_id, client in clients:
            if not client.connected:
                dead.append(client_id)
                continue

            # Dedup check
            event_id = envelope.get("event_id", "")
            if event_id in client.seen_ids:
                continue
            client.seen_ids[event_id] = True
            if len(client.seen_ids) > DEDUP_HISTORY:
                client.seen_ids.popitem(last=False)

            # Queue if not full, else drop client
            if client.queue.full():
                logger.warning("ws.client_queue_full", user_id=client.user_id)
                dead.append(client_id)
                client.connected = False
            else:
                try:
                    client.queue.put_nowait(envelope)
                except asyncio.QueueFull:
                    dead.append(client_id)
                    client.connected = False

        # Clean up dead clients
        async with self._lock:
            for cid in dead:
                self._clients.pop(cid, None)

    async def _sender_loop(self, client_id: str, client: ClientState) -> None:
        """Send queued messages to a specific client."""
        while client.connected:
            try:
                try:
                    envelope = await asyncio.wait_for(client.queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                if client.websocket.client_state == WebSocketState.CONNECTED:
                    await client.websocket.send_json(envelope)
                else:
                    break
            except (WebSocketDisconnect, RuntimeError):
                break
            except Exception as exc:
                logger.error("ws.send_error", error=str(exc))
                break

        client.connected = False
        async with self._lock:
            self._clients.pop(client_id, None)

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats and check for dead clients."""
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)

            async with self._lock:
                clients = list(self._clients.items())

            dead = []
            now = datetime.now(UTC)

            for client_id, client in clients:
                if not client.connected:
                    dead.append(client_id)
                    continue

                age = (now - client.last_heartbeat).total_seconds()
                if age > HEARTBEAT_INTERVAL * (MAX_MISSED_HEARTBEATS + 1):
                    logger.warning("ws.client_dead", user_id=client.user_id)
                    dead.append(client_id)
                    client.connected = False
                    continue

                # Send ping
                ping = {
                    "event": "PING",
                    "event_id": str(uuid.uuid4()),
                    "emitted_at": now.isoformat(),
                    "patient_code": None,
                    "payload": {"ts": now.isoformat()},
                }
                try:
                    client.queue.put_nowait(ping)
                except asyncio.QueueFull:
                    dead.append(client_id)
                    client.connected = False

            async with self._lock:
                for cid in dead:
                    self._clients.pop(cid, None)

            if not self._clients:
                self._heartbeat_task = None
                break

    async def handle_pong(self, client: ClientState) -> None:
        client.last_heartbeat = datetime.now(UTC)
        client.missed_heartbeats = 0


# Singleton
ws_manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, token: str = ""):
    """Main WebSocket endpoint handler."""
    client = await ws_manager.connect(websocket, token)
    if client is None:
        return  # Authentication failed, connection closed

    try:
        while client.connected:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
                if data.get("event") == "PONG":
                    await ws_manager.handle_pong(client)
            except asyncio.TimeoutError:
                continue
            except WebSocketDisconnect:
                break
            except Exception:
                break
    finally:
        await ws_manager.disconnect(client)
