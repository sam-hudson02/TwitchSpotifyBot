from utils.errors import BadLink


class TrackInfo:
    def __init__(self, info: dict):
        self.track: str = self._get_track(info)
        self.artist: str = self._get_artist(info)
        self.link: str = self._get_link(info)

    def _get_track(self, info: dict) -> str:
        try:
            track = info['name']
            return track
        except KeyError:
            raise BadLink

    def _get_artist(self, info: dict) -> str:
        try:
            artists_info_all = info['artists']
            artists = []
            for artist_info in artists_info_all:
                artist = artist_info['name']
                artists.append(artist)
            str_artists = ', '.join(artists)
            return str_artists
        except KeyError:
            raise BadLink

    def _get_link(self, info: dict) -> str:
        try:
            link = info['external_urls']['spotify']
            return link
        except KeyError:
            raise BadLink
