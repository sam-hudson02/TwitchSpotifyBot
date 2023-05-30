from utils.errors import NoCurrentTrack


class TrackContext:
    def __init__(self, info: dict):
        self.track: str = self._get_track(info)
        self.artist: str = self._get_artist(info)
        self.progress: int = self._get_progress(info)
        self.duration: int = self._get_duration(info)
        self.album_art: str = self._get_album_art(info)
        self.playlist: str | None = self._get_playlist(info)
        self.playback_id: str = self._get_playback_id(info)
        self.paused: bool = self._get_paused(info)

    def _get_track(self, info: dict) -> str:
        try:
            track = info['item']['name']
            return track
        except KeyError:
            raise NoCurrentTrack

    def _get_artist(self, info: dict) -> str:
        try:
            artists_info_all = info['item']['artists']
            artists = []
            for artist_info in artists_info_all:
                artist = artist_info['name']
                artists.append(artist)
            str_artists = ', '.join(artists)
            return str_artists
        except KeyError:
            raise NoCurrentTrack

    def _get_progress(self, info: dict) -> int:
        try:
            prog = int(info['progress_ms'])
            return prog
        except (KeyError, TypeError, ValueError):
            raise NoCurrentTrack

    def _get_duration(self, info: dict) -> int:
        try:
            length = int(info['item']['duration_ms'])
            return length
        except (KeyError, TypeError, ValueError):
            raise NoCurrentTrack

    def _get_album_art(self, info: dict) -> str:
        try:
            image = info['item']['album']['images'][0]['url']
            return image
        except KeyError:
            raise NoCurrentTrack

    def _get_playlist(self, info: dict) -> str | None:
        try:
            playlist = info['context']['external_urls']['spotify']
            return playlist
        except Exception:
            return None

    def _get_playback_id(self, info: dict) -> str:
        try:
            track_id = info['item']['id']
            return track_id
        except KeyError:
            raise NoCurrentTrack

    def _get_paused(self, info: dict) -> bool:
        try:
            playing = bool(info['is_playing'])
            return not playing
        except KeyError:
            raise NoCurrentTrack
