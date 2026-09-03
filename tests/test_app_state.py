import unittest
from functools import partial

from utils.logger import Log
from server.state import AppState
from mocks.mock_services import (MockSpotify, MockTwitchBot, MockDiscordBot,
                                 MockDB, MockQueueDB, queue_row, mock_creds,
                                 mock_services)


def build_state(*, spotify_connected=True, twitch_start_ok=True,
                discord_start_ok=True, twitch_factory=None, creds=None,
                db=None):
    db = db if db is not None else MockDB()
    services = mock_services(spotify=MockSpotify(connected=spotify_connected),
                             creds=creds or mock_creds(), db=db)
    state = AppState(
        log=Log('test'),
        services=services,
        twitch_factory=twitch_factory or partial(MockTwitchBot,
                                                  start_ok=twitch_start_ok),
        discord_factory=partial(MockDiscordBot, start_ok=discord_start_ok),
    )
    return state, db


class TestAppState(unittest.IsolatedAsyncioTestCase):
    async def test_startup_starts_both_when_spotify_connected(self):
        state, db = build_state(spotify_connected=True)
        await state.startup()
        self.assertTrue(db.connected)
        self.assertTrue(state.twitch_running)
        self.assertTrue(state.discord_running)

    async def test_startup_skips_twitch_when_spotify_disconnected(self):
        state, _ = build_state(spotify_connected=False)
        await state.startup()
        self.assertFalse(state.twitch_running)
        # discord does not depend on spotify
        self.assertTrue(state.discord_running)

    async def test_start_twitch_requires_spotify(self):
        state, _ = build_state(spotify_connected=False)
        ok, message = await state.start_twitch()
        self.assertFalse(ok)
        self.assertEqual(message, 'Spotify is not connected')
        self.assertFalse(state.twitch_running)

    async def test_twitch_stop_then_restart(self):
        state, _ = build_state()
        await state.startup()
        self.assertTrue(state.twitch_running)

        ok, message = await state.stop_twitch()
        self.assertTrue(ok)
        self.assertEqual(message, 'stopped')
        self.assertFalse(state.twitch_running)

        ok, message = await state.start_twitch()
        self.assertTrue(ok)
        self.assertEqual(message, 'started')
        self.assertTrue(state.twitch_running)

    async def test_start_twitch_is_idempotent(self):
        state, _ = build_state()
        await state.startup()
        ok, message = await state.start_twitch()
        self.assertTrue(ok)
        self.assertEqual(message, 'already running')

    async def test_factory_error_surfaces_at_construction(self):
        # the Twitch bot is built eagerly in AppState.__init__, so a
        # construction failure surfaces there rather than at start time
        def boom(services):
            raise RuntimeError('bad token')

        with self.assertRaises(RuntimeError):
            build_state(twitch_factory=boom)

    async def test_start_twitch_handles_start_error(self):
        state, _ = build_state(twitch_start_ok=False)
        ok, message = await state.start_twitch()
        self.assertFalse(ok)
        self.assertIn('bad token', message)
        self.assertFalse(state.twitch_running)

    async def test_discord_start_failure_leaves_it_stopped(self):
        state, _ = build_state(discord_start_ok=False)
        ok, _ = await state.start_discord()
        self.assertFalse(ok)
        self.assertFalse(state.discord_running)

    async def test_discord_requires_webhooks(self):
        state, _ = build_state(creds=mock_creds(queue_webhook=None,
                                                leaderboard_webhook=None))
        ok, message = await state.start_discord()
        self.assertFalse(ok)
        self.assertEqual(message, 'No Discord webhooks configured')

    async def _queue_ids(self, state):
        return [q['id'] for q in await state.queue_snapshot()]

    async def test_queue_move_to_front(self):
        db = MockQueueDB([queue_row(10, 1), queue_row(20, 2), queue_row(30, 3)])
        state, _ = build_state(db=db)
        await state.queue_move(30, None)
        self.assertEqual(await self._queue_ids(state), [30, 10, 20])

    async def test_queue_move_to_middle(self):
        db = MockQueueDB([queue_row(10, 1), queue_row(20, 2), queue_row(30, 3)])
        state, _ = build_state(db=db)
        # move 10 to just after 20
        await state.queue_move(10, 20)
        self.assertEqual(await self._queue_ids(state), [20, 10, 30])

    async def test_queue_move_to_end(self):
        db = MockQueueDB([queue_row(10, 1), queue_row(20, 2), queue_row(30, 3)])
        state, _ = build_state(db=db)
        await state.queue_move(10, 30)
        self.assertEqual(await self._queue_ids(state), [20, 30, 10])

    async def test_queue_move_unknown_id_raises(self):
        db = MockQueueDB([queue_row(10, 1)])
        state, _ = build_state(db=db)
        with self.assertRaises(ValueError):
            await state.queue_move(999, None)

    async def test_queue_remove(self):
        db = MockQueueDB([queue_row(10, 1), queue_row(20, 2)])
        state, _ = build_state(db=db)
        await state.queue_remove(10)
        self.assertEqual(await self._queue_ids(state), [20])

    async def test_queue_clear(self):
        db = MockQueueDB([queue_row(10, 1), queue_row(20, 2)])
        state, _ = build_state(db=db)
        await state.queue_clear()
        self.assertEqual(await self._queue_ids(state), [])

    async def test_skip_delegates_to_twitch(self):
        db = MockQueueDB([queue_row(10, 1)])
        state, _ = build_state(db=db)
        state.twitch = MockTwitchBot()
        await state.skip()
        self.assertTrue(state.twitch.skipped)

    async def test_queue_add_uses_broadcaster_as_requester(self):
        db = MockQueueDB([])
        state, _ = build_state(db=db, creds=mock_creds(channel='streamer'))
        state.twitch = MockTwitchBot()
        info = await state.queue_add('a song')
        self.assertEqual(state.twitch.added, ('a song', 'streamer'))
        self.assertEqual(info.track, 'a song')

    async def test_now_playing_returns_context(self):
        from types import SimpleNamespace
        state, _ = build_state()
        snapshot = {'track': 'song', 'artist': 'artist', 'requester': 'user'}
        state.services.context = SimpleNamespace(get_context=lambda: snapshot)
        self.assertEqual(state.now_playing(), snapshot)

    async def test_set_active_updates_settings_and_context(self):
        from types import SimpleNamespace
        state, _ = build_state()
        applied = []
        state.services.settings = SimpleNamespace(
            set_active=lambda a: applied.append(a))
        state.services.context = SimpleNamespace(active=True)
        state.set_active(False)
        self.assertEqual(applied, [False])
        self.assertFalse(state.services.context.active)

    async def test_shutdown_stops_services_and_disconnects_db(self):
        state, db = build_state()
        await state.startup()
        twitch, discord = state.twitch, state.discord
        await state.shutdown()
        self.assertTrue(twitch.stopped)
        self.assertTrue(discord.stopped)
        self.assertFalse(db.connected)
        self.assertFalse(state.twitch_running)
        self.assertFalse(state.discord_running)


if __name__ == '__main__':
    unittest.main()
