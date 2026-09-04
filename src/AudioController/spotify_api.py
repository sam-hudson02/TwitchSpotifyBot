import json
import os

import spotipy
from spotipy.oauth2 import CacheFileHandler

from utils import SpotifyCreds
from utils.errors import BadLink, NoCurrentTrack, TrackNotFound
from AudioController.track_info import TrackInfo
from AudioController.track_context import TrackContext
from utils.logger import Log
from services.interfaces import SpotifyInterface


class Spotify(SpotifyInterface):
    def __init__(self, creds: SpotifyCreds):
        self.log = Log('Spotify')
        self.user = creds.username
        self.client_id = creds.client_id
        self.secret = creds.client_secret
        self.scopes = creds.scopes
        self.cache_path = f'./secret/.cache-{self.user}'
        self.cache_handler = CacheFileHandler(cache_path=self.cache_path)
        self._auth = None
        self._sp = spotipy.Spotify(auth_manager=self.oauth())
        self.connected = False

    # connection / authorization ------------------------------------------

    def oauth(self, redirect_uri: str = 'https://open.spotify.com/') \
            -> spotipy.SpotifyOAuth:
        return spotipy.SpotifyOAuth(client_id=self.client_id,
                                    client_secret=self.secret,
                                    redirect_uri=redirect_uri,
                                    cache_handler=self.cache_handler,
                                    open_browser=False,
                                    scope=self.scopes)

    def connect(self) -> bool:
        self.connected = self._validate_cache()
        return self.connected

    def is_connected(self) -> bool:
        return self.connected

    def _validate_cache(self) -> bool:
        self.log.info('Validating cached Spotify token')

        if not os.path.exists(self.cache_path):
            self.log.info('No cached Spotify token found')
            return False

        try:
            with open(self.cache_path, 'r') as f:
                cache_data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            self.log.error(f'Could not read cached Spotify token: {e}')
            return False

        if cache_data.get('access_token') is None \
                or cache_data.get('refresh_token') is None:
            self.log.error('Cached Spotify token is missing access or '
                           'refresh token')
            return False

        if self.verify():
            self.log.info('Cached Spotify token is valid')
            return True

        self.log.error('Cached Spotify token is invalid')
        return False

    def verify(self) -> bool:
        """Confirm the credentials work by making a real API call.

        spotipy refreshes an expired access token from the cached refresh
        token, so this works both after an interactive login and on startup."""
        try:
            self._sp.current_user()
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
        self._auth = self.oauth(redirect_uri)
        return self._auth.get_authorize_url()

    def handle_callback(self, request_url: str) -> bool:
        self.log.info('Spotify callback')
        if self._auth is None:
            self.log.error('Spotify authorization was not initiated')
            return False

        try:
            self.log.info('Getting access token')
            code = self._auth.parse_response_code(request_url)
            self._auth.get_access_token(code, as_dict=False, check_cache=False)
        except Exception as e:
            self.log.error(f'Failed to get Spotify access token: {e}')
            return False

        if not self.verify():
            return False

        self.connected = True
        return True

    # playback / queries --------------------------------------------------

    def search_song(self, query) -> str:
        try:
            results = self._sp.search(query, limit=1, type='track')
            if results is None:
                raise TrackNotFound
            url = results['tracks']['items'][0]['external_urls']['spotify']
            return url
        except IndexError:
            raise TrackNotFound

    def get_track_info(self, url: str) -> TrackInfo:
        info = self._sp.track(url)
        if info is None:
            raise BadLink
        return TrackInfo(info)

    @staticmethod
    def get_track_info_list(info_all: list[dict]) -> list[TrackInfo]:
        track_info_all: list[TrackInfo] = []
        for info in info_all:
            track_info_all.append(TrackInfo(info))
        return track_info_all

    def get_current_track(self) -> TrackInfo:
        try:
            info = self._sp.current_user_playing_track()
            if info is None:
                raise NoCurrentTrack
            info = info['item']
            return TrackInfo(info)
        except BadLink:
            raise NoCurrentTrack

    def get_recent_plays(self) -> list[TrackInfo]:
        recent = self._sp.current_user_recently_played(limit=10)
        if recent is None:
            return []
        info_all = recent['items']
        info: list[TrackInfo] = []
        for track_info in self.get_track_info_list(info_all):
            info.append(track_info)
        return info

    def get_track_link(self, request) -> str:
        request = request.replace(' by ', ' ')
        request = request.strip('-')
        song_link = self.search_song(request)
        if song_link is None:
            raise TrackNotFound
        return song_link

    def skip(self):
        info = self.get_current_track()
        self._sp.next_track()
        return info

    def get_context(self) -> TrackContext:
        try:
            info = self._sp.current_user_playing_track()
            if info is None:
                raise NoCurrentTrack
            return TrackContext(info)
        except TypeError as er:
            self.log.error(er)
            raise NoCurrentTrack

    def next(self) -> None:
        self._sp.next_track()

    def play_pause(self) -> bool:
        playback = self._sp.current_playback()
        if playback is None:
            return False
        if playback['is_playing']:
            self._sp.pause_playback()
            return True
        else:
            self._sp.start_playback()
            return False

    def play(self, link) -> None:
        try:
            self._sp.start_playback(uris=[link])
        except spotipy.exceptions.SpotifyException:
            pass

    def get_queue(self) -> list[str]:
        info = self._sp.queue()
        if info is None:
            return []
        queue = info['queue']
        queue_info = []
        for track in queue:
            queue_info.append(track['id'])
        return queue_info

    def add_to_queue(self, link) -> None:
        self._sp.add_to_queue(link)
