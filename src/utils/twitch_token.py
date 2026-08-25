import asyncio
import json
import os
import time
from typing import Optional
import aiohttp
from utils.creds import TwitchCreds
from utils.logger import Log

TOKEN_URL = 'https://id.twitch.tv/oauth2/token'

# refresh this many seconds before the token actually expires
EXPIRY_BUFFER = 300


class TwitchToken:
    """Manages a Twitch user access token, refreshing it via the OAuth
    refresh-token grant and caching the (rotating) refresh token on disk."""

    def __init__(self, creds: TwitchCreds, log: Optional[Log] = None,
                 cache_path: str = './secret/.twitch-token.json'):
        self.creds = creds
        self.log = log or Log('TwitchToken')
        self.cache_path = cache_path
        self._lock = asyncio.Lock()
        self._access_token: Optional[str] = creds.access_token
        self._refresh_token: str = creds.refresh_token
        # 0 means "unknown expiry" (e.g. a token pasted into conf.env); such a
        # token is used until it fails rather than refreshed pre-emptively.
        self._expires_at: float = 0.0
        self._load_cache()

    def _load_cache(self) -> None:
        if not os.path.exists(self.cache_path):
            return
        try:
            with open(self.cache_path) as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            self.log.error(f'Could not read token cache: {e}')
            return
        # cached values are newer than whatever is in conf.env
        self._access_token = data.get('access_token', self._access_token)
        self._refresh_token = data.get('refresh_token', self._refresh_token)
        self._expires_at = data.get('expires_at', 0.0)

    def _save_cache(self) -> None:
        data = {
            'access_token': self._access_token,
            'refresh_token': self._refresh_token,
            'expires_at': self._expires_at,
        }
        try:
            os.makedirs(os.path.dirname(self.cache_path) or '.', exist_ok=True)
            with open(self.cache_path, 'w') as f:
                json.dump(data, f)
        except OSError as e:
            self.log.error(f'Could not write token cache: {e}')

    def _expired(self) -> bool:
        if self._access_token is None:
            return True
        if self._expires_at <= 0:
            # unknown expiry: trust it until a request/connection is rejected
            return False
        return time.time() >= self._expires_at - EXPIRY_BUFFER

    async def get(self, force: bool = False) -> str:
        async with self._lock:
            if force or self._expired():
                await self._refresh()
            assert self._access_token is not None
            return self._access_token

    async def _refresh(self) -> None:
        # Prefer the cached/current refresh token, but fall back to the one in
        # conf.env so re-pasting a fresh token after a revocation recovers
        # without having to delete the cache file.
        candidates = [self._refresh_token]
        if self.creds.refresh_token not in candidates:
            candidates.append(self.creds.refresh_token)

        last_error: Optional[str] = None
        for refresh_token in candidates:
            try:
                await self._do_refresh(refresh_token)
                self.log.info('Refreshed Twitch access token')
                return
            except Exception as e:
                last_error = str(e)
                self.log.error(f'Token refresh failed: {e}')
        raise RuntimeError(f'Could not refresh Twitch token: {last_error}')

    async def _do_refresh(self, refresh_token: str) -> None:
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': self.creds.client_id,
        }
        if self.creds.client_secret:
            payload['client_secret'] = self.creds.client_secret

        async with aiohttp.ClientSession() as session:
            async with session.post(TOKEN_URL, data=payload) as resp:
                body = await resp.json()
                if resp.status != 200:
                    message = body.get('message', body) \
                        if isinstance(body, dict) else body
                    raise RuntimeError(f'{resp.status}: {message}')

        self._access_token = body['access_token']
        # refresh tokens may rotate; always keep the newest one
        self._refresh_token = body.get('refresh_token', refresh_token)
        self._expires_at = time.time() + body.get('expires_in', 0)
        self._save_cache()
