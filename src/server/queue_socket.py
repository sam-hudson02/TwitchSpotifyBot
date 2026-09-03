import asyncio
from typing import Awaitable, Callable

from fastapi import WebSocket

Snapshot = Callable[[], Awaitable[list[dict]]]


class QueueSocket:
    """Tracks the live queue-editor WebSocket clients and pushes queue updates.

    While any client is connected a poll loop watches the queue so changes made
    outside the socket (e.g. songs the Twitch bot adds) are pushed too; it stops
    when the last client disconnects."""

    def __init__(self, snapshot: Snapshot):
        self._snapshot = snapshot
        self.connections: set[WebSocket] = set()
        self._poll_task: asyncio.Task | None = None
        self._last: list[dict] | None = None

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.connections.add(ws)
        self._last = await self._snapshot()
        await ws.send_json({'queue': self._last})
        if self._poll_task is None:
            self._poll_task = asyncio.create_task(self._poll())

    def disconnect(self, ws: WebSocket) -> None:
        self.connections.discard(ws)
        if not self.connections and self._poll_task is not None:
            self._poll_task.cancel()
            self._poll_task = None

    async def broadcast(self, payload: dict) -> None:
        for ws in list(self.connections):
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(ws)

    async def broadcast_queue(self) -> None:
        self._last = await self._snapshot()
        await self.broadcast({'queue': self._last})

    async def _poll(self) -> None:
        try:
            while True:
                await asyncio.sleep(2)
                snap = await self._snapshot()
                if snap != self._last:
                    self._last = snap
                    await self.broadcast({'queue': snap})
        except asyncio.CancelledError:
            pass
