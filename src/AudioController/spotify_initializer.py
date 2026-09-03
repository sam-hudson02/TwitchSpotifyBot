import json
import os
from spotipy.oauth2 import CacheFileHandler
from spotipy import Spotify as SpotifyClient, SpotifyOAuth
from AudioController.spotify_api import Spotify
from utils import Log, SpotifyCreds


class SpotifyInitial:
    def __init__(self, creds: SpotifyCreds):
        self.log = Log('SpotifyInit', file='./data/spotify_init.log')
        self.creds = creds
        self.cache_path = f'./secret/.cache-{creds.username}'
        self.cache_handler = CacheFileHandler(cache_path=self.cache_path)
        self.oauth: SpotifyOAuth | None = None
        self.connected = self.validate_cache()

    def validate_cache(self) -> bool:
        self.log.info('Validating cached Spotify token')

        if not os.path.exists(self.cache_path):
            self.log.info('No cached Spotify token found')
            return False

        with open(self.cache_path, 'r') as f:
            cache_data = json.load(f)

            if cache_data.get('access_token') is None \
                    or cache_data.get('refresh_token') is None:
                self.log.error('Cached Spotify token is missing access or '
                               'refresh token')

            if self.test_spotify():
                self.log.info('Cached Spotify token is valid')
                return True

            self.log.error('Cached Spotify token is invalid')
            json.dump({}, f)

        return False

    def spotify_oauth(self, redirect_uri: str = 'https://open.spotify.com/') \
            -> SpotifyOAuth:
        return SpotifyOAuth(client_id=self.creds.client_id,
                            client_secret=self.creds.client_secret,
                            redirect_uri=redirect_uri,
                            scope=self.creds.scopes,
                            cache_handler=self.cache_handler)

    def test_spotify(self) -> bool:
        """Confirm the cached Spotify token works by making a real API call.

        Builds an OAuth manager around the cache handler so it works both after
        the interactive login and on startup from a cached token; spotipy
        refreshes an expired access token using the cached refresh token."""
        try:
            sp = SpotifyClient(auth_manager=self.spotify_oauth())
            sp.current_user()
            self.log.info('Spotify credentials verified')
            return True
        except Exception as e:
            self.log.error(f'Spotify credential check failed: {e}')
            return False

    def authorize_url(self, base_url: str) -> str:
        redirect_uri = base_url + 'callback'
        # Spotify no longer accepts "localhost" as a redirect host; the loopback
        # IP literal is required, so rewrite it transparently if the user
        # browsed to localhost instead of 127.0.0.1.
        redirect_uri = redirect_uri.replace('://localhost:', '://127.0.0.1:')
        self.oauth = self.spotify_oauth(redirect_uri)
        return self.oauth.get_authorize_url()

    def handle_callback(self, request_url: str) -> bool:
        self.log.info('Spotify callback')
        if self.oauth is None:
            self.log.error('Spotify OAuth not initialized')
            return False

        try:
            self.log.info('Getting access token')
            code = self.oauth.parse_response_code(request_url)
            self.oauth.get_access_token(code, as_dict=False, check_cache=False)
        except Exception as e:
            self.log.error(f'Failed to get Spotify access token: {e}')
            return False

        if not self.test_spotify():
            return False

        self.connected = True
        return True

    def get_spotify(self) -> Spotify:
        return Spotify(self.creds)
