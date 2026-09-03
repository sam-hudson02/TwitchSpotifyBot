import asyncio
import unittest

from server.queue_socket import QueueSocket


class FakeWebSocket:
    def __init__(self, fail=False):
        self.sent = []
        self.accepted = False
        self._fail = fail

    async def accept(self):
        self.accepted = True

    async def send_json(self, payload):
        if self._fail:
            raise RuntimeError('closed')
        self.sent.append(payload)


class TestQueueSocket(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.snap = [{'id': 1, 'position': 1.0}]

        async def snapshot():
            return self.snap

        self.socket = QueueSocket(snapshot)

    async def asyncTearDown(self):
        # stop the poll loop if a connection started it
        for ws in list(self.socket.connections):
            self.socket.disconnect(ws)

    async def test_connect_accepts_and_sends_snapshot(self):
        ws = FakeWebSocket()
        await self.socket.connect(ws)
        self.assertTrue(ws.accepted)
        self.assertIn(ws, self.socket.connections)
        self.assertEqual(ws.sent[-1], {'queue': self.snap})

    async def test_connect_starts_poll_disconnect_stops_it(self):
        ws = FakeWebSocket()
        await self.socket.connect(ws)
        self.assertIsNotNone(self.socket._poll_task)
        self.socket.disconnect(ws)
        self.assertNotIn(ws, self.socket.connections)
        self.assertIsNone(self.socket._poll_task)

    async def test_broadcast_to_all(self):
        a, b = FakeWebSocket(), FakeWebSocket()
        await self.socket.connect(a)
        await self.socket.connect(b)
        await self.socket.broadcast({'hello': 1})
        self.assertIn({'hello': 1}, a.sent)
        self.assertIn({'hello': 1}, b.sent)

    async def test_broadcast_drops_failed_client(self):
        good, bad = FakeWebSocket(), FakeWebSocket(fail=True)
        await self.socket.connect(good)
        self.socket.connections.add(bad)  # add a client that errors on send
        await self.socket.broadcast({'x': 1})
        self.assertNotIn(bad, self.socket.connections)
        self.assertIn(good, self.socket.connections)

    async def test_poll_broadcasts_on_change(self):
        ws = FakeWebSocket()
        await self.socket.connect(ws)
        before = len(ws.sent)
        self.snap = [{'id': 2, 'position': 1.0}]  # change the snapshot
        await asyncio.sleep(2.2)  # let the poll loop pick it up
        self.assertGreater(len(ws.sent), before)
        self.assertEqual(ws.sent[-1], {'queue': self.snap})


if __name__ == '__main__':
    unittest.main()
