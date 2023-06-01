import spotipy
from utils import SpotifyCreds
from utils.errors import BadLink, NoCurrentTrack, TrackNotFound
from AudioController.track_info import TrackInfo
from AudioController.track_context import TrackContext
from utils.logger import Log


class Spotify:
    def __init__(self, creds: SpotifyCreds):
        self.log = Log('Spotify')
        self.user = creds.username
        self.client_id = creds.client_id
        self.secret = creds.client_secret
        self.scopes = creds.scopes
        self.token = self.get_token()
        self._sp = self.auth()
        self._sp.search(q='test')

    def get_token(self):
        cache_path = f'./secret/.cache-{self.user}'
        handler = spotipy.oauth2.CacheFileHandler(cache_path=cache_path,
                                                  username=self.user)

        return spotipy.SpotifyOAuth(client_id=self.client_id,
                                    client_secret=self.secret,
                                    redirect_uri='https://open.spotify.com/',
                                    cache_handler=handler,
                                    open_browser=False,
                                    scope=self.scopes)

    def auth(self):
        return spotipy.Spotify(auth_manager=self.token)

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
