import spotipy
from utils import SpotifyCreds
from utils.errors import BadLink, NoCurrentTrack, TrackNotFound
from AudioController.track_info import TrackInfo
from AudioController.track_context import TrackContext


class Spotify:
    def __init__(self, creds: SpotifyCreds):
        self.user = creds.username
        self.client_id = creds.client_id
        self.secret = creds.client_secret
        self.token = self.get_token()
        self.sp = self.auth()
        self.sp.search(q='test')

    def get_token(self):
        cache_path = f'./secret/.cache-{self.user}'
        handler = spotipy.oauth2.CacheFileHandler(cache_path=cache_path,
                                                  username=self.user)

        scopes = 'user-modify-playback-state user-read-playback-state ' \
                 'user-read-currently-playing user-read-playback-position' \
                 ' user-read-recently-played streaming'

        return spotipy.SpotifyOAuth(client_id=self.client_id,
                                    client_secret=self.secret,
                                    redirect_uri='https://open.spotify.com/',
                                    cache_handler=handler,
                                    open_browser=False, scope=scopes)

    def auth(self):
        return spotipy.Spotify(auth_manager=self.token)

    def search_song(self, query) -> str:
        try:
            results = self.sp.search(query, limit=1, type='track')
            if results is None:
                raise TrackNotFound
            url = results['tracks']['items'][0]['external_urls']['spotify']
            return url
        except IndexError:
            raise TrackNotFound

    def get_track_info(self, url: str) -> TrackInfo:
        info = self.sp.track(url)
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
            info = self.sp.current_user_playing_track()
            if info is None:
                raise NoCurrentTrack
            info = info['item']
            return TrackInfo(info)
        except BadLink:
            raise NoCurrentTrack

    def get_recent_plays(self) -> list[TrackInfo]:
        recent = self.sp.current_user_recently_played(limit=10)
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
        self.sp.next_track()
        return info

    def get_context(self) -> TrackContext:
        try:
            info = self.sp.current_user_playing_track()
            if info is None:
                raise NoCurrentTrack
            return TrackContext(info)
        except TypeError as er:
            print(er)
            raise NoCurrentTrack

    def next(self) -> None:
        self.sp.next_track()

    def play_pause(self) -> bool:
        playback = self.sp.current_playback()
        if playback is None:
            return False
        if playback['is_playing']:
            self.sp.pause_playback()
            return True
        else:
            self.sp.start_playback()
            return False

    def play(self, link) -> None:
        try:
            self.sp.start_playback(uris=[link])
        except spotipy.exceptions.SpotifyException:
            pass

    def get_queue(self) -> list[str]:
        info = self.sp.queue()
        if info is None:
            return []
        queue = info['queue']
        queue_info = []
        for track in queue:
            queue_info.append(track['id'])
        print(queue_info)
        return queue_info
