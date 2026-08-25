import json
import os
import tempfile
import time
import unittest
from utils.twitch_token import TwitchToken


class StubCreds:
    def __init__(self, access_token='access0', refresh_token='refresh0',
                 client_id='cid', client_secret=None):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret


def make_token(**kwargs):
    # a temp cache path that does not exist yet
    fd, path = tempfile.mkstemp(suffix='.json')
    os.close(fd)
    os.remove(path)
    return TwitchToken(StubCreds(**kwargs), cache_path=path), path


class TestTwitchTokenLogic(unittest.TestCase):
    def test_seeds_from_creds_when_no_cache(self):
        token, _ = make_token(access_token='a', refresh_token='r')
        self.assertEqual(token._access_token, 'a')
        self.assertEqual(token._refresh_token, 'r')
        self.assertEqual(token._expires_at, 0.0)

    def test_expired_logic(self):
        token, _ = make_token()
        # unknown expiry -> use it until it fails
        token._expires_at = 0
        self.assertFalse(token._expired())
        # comfortably in the future -> valid
        token._expires_at = time.time() + 10000
        self.assertFalse(token._expired())
        # within the refresh buffer -> expired
        token._expires_at = time.time() + 10
        self.assertTrue(token._expired())
        # no access token -> expired regardless
        token._access_token = None
        token._expires_at = time.time() + 10000
        self.assertTrue(token._expired())

    def test_cache_is_preferred_over_confenv(self):
        fd, path = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        with open(path, 'w') as f:
            json.dump({'access_token': 'cached_a',
                       'refresh_token': 'cached_r',
                       'expires_at': 123.0}, f)
        token = TwitchToken(StubCreds(access_token='env_a',
                                      refresh_token='env_r'),
                            cache_path=path)
        self.assertEqual(token._access_token, 'cached_a')
        self.assertEqual(token._refresh_token, 'cached_r')
        self.assertEqual(token._expires_at, 123.0)
        os.remove(path)


class TestTwitchTokenRefresh(unittest.IsolatedAsyncioTestCase):
    async def test_get_uses_existing_token_without_refresh(self):
        token, _ = make_token(access_token='a')
        calls = []

        async def fake(refresh_token):
            calls.append(refresh_token)
        token._do_refresh = fake

        self.assertEqual(await token.get(), 'a')
        self.assertEqual(calls, [])  # not expired -> no refresh

    async def test_force_refresh_persists_rotated_token(self):
        token, path = make_token(access_token='old', refresh_token='r0')

        async def fake(refresh_token):
            token._access_token = 'new'
            token._refresh_token = 'r1'  # Twitch rotated the refresh token
            token._expires_at = time.time() + 3600
            token._save_cache()
        token._do_refresh = fake

        self.assertEqual(await token.get(force=True), 'new')
        with open(path) as f:
            data = json.load(f)
        self.assertEqual(data['access_token'], 'new')
        self.assertEqual(data['refresh_token'], 'r1')
        os.remove(path)

    async def test_refresh_falls_back_to_confenv_token(self):
        token, _ = make_token(refresh_token='env_r')
        token._refresh_token = 'stale_cached_r'  # simulate a stale cache
        attempts = []

        async def fake(refresh_token):
            attempts.append(refresh_token)
            if refresh_token == 'stale_cached_r':
                raise RuntimeError('invalid refresh token')
            token._access_token = 'new'
        token._do_refresh = fake

        self.assertEqual(await token.get(force=True), 'new')
        self.assertEqual(attempts, ['stale_cached_r', 'env_r'])


if __name__ == '__main__':
    unittest.main()
