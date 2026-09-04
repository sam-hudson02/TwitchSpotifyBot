import unittest
from types import SimpleNamespace

from AudioController.audio_controller import AudioController, Context
from utils.errors import NoCurrentTrack
from utils.logger import Log


class FakeSpot:
    def __init__(self):
        self.next_calls = 0
        self.queue = []
        # None -> "nothing playing"; a list -> playback ids read in sequence
        self.playback_seq = None

    def get_queue(self):
        return self.queue

    def add_to_queue(self, url):
        self.queue.append(url.split('/')[-1])

    def next(self):
        self.next_calls += 1

    def get_context(self):
        if self.playback_seq is None:
            return None
        pid = self.playback_seq.pop(0) if self.playback_seq else None
        if pid is None:
            raise NoCurrentTrack
        return SimpleNamespace(playback_id=pid)


class FakeDB:
    def __init__(self, rows=None):
        self.rows = list(rows) if rows else []

    async def get_queue(self):
        return self.rows

    async def remove_from_queue(self, req_id):
        self.rows = [r for r in self.rows if r.id != req_id]


class TestPlayNextSkip(unittest.IsolatedAsyncioTestCase):
    def build(self, rows=None, playing_queue=False):
        ctx = Context()
        ctx.live = True
        ctx.active = True
        ctx.playing_queue = playing_queue
        ctx.requester = 'user' if playing_queue else None
        spot = FakeSpot()
        return AudioController(FakeDB(rows), spot, ctx, Log('test')), spot, ctx

    async def test_skip_requested_song_with_empty_queue_advances(self):
        # a requested song is playing and nothing else is queued: an explicit
        # skip must still advance on Spotify, not just flip playing_queue
        ac, spot, ctx = self.build(rows=[], playing_queue=True)
        await ac.play_next(skipped=True)
        self.assertEqual(spot.next_calls, 1)
        self.assertFalse(ctx.playing_queue)
        self.assertIsNone(ctx.requester)

    async def test_natural_end_of_requested_song_does_not_skip(self):
        # the song ended on its own (skipped=False): fall back to the playlist
        # without calling next()
        ac, spot, ctx = self.build(rows=[], playing_queue=True)
        await ac.play_next(skipped=False)
        self.assertEqual(spot.next_calls, 0)
        self.assertFalse(ctx.playing_queue)

    async def test_skip_playlist_song_with_empty_queue_advances(self):
        ac, spot, ctx = self.build(rows=[], playing_queue=False)
        await ac.play_next(skipped=True)
        self.assertEqual(spot.next_calls, 1)

    async def test_set_requester_polls_until_spotify_catches_up(self):
        ac, spot, ctx = self.build(rows=[])
        ac.requester_poll_interval = 0
        # Spotify reports the previous track twice, then the new one
        spot.playback_seq = ['old', 'old', 'newid']
        song = SimpleNamespace(url='https://open.spotify.com/track/newid',
                               requester='alice', songName='song')
        await ac.set_requester(song)
        self.assertEqual(ctx.requester, 'alice')
        self.assertTrue(ctx.playing_queue)
        self.assertEqual(ctx.playback_id, 'newid')

    async def test_set_requester_gives_up_after_attempts(self):
        ac, spot, ctx = self.build(rows=[])
        ac.requester_poll_interval = 0
        ac.requester_poll_attempts = 3
        # Spotify never reports the requested track
        spot.playback_seq = ['old', 'old', 'old', 'old']
        song = SimpleNamespace(url='https://open.spotify.com/track/newid',
                               requester='alice', songName='song')
        await ac.set_requester(song)
        self.assertIsNone(ctx.requester)


if __name__ == '__main__':
    unittest.main()
