from spotify_api import Spotify
from db_handler import DB
from errors import *
from spotify_api import Spotify


class AudioController:
    def __init__(self, db: DB, spot: Spotify):
        self.db = db
        self.spot = spot
        self.context = None

    def add_to_queue(self, request: str, user: str):

        # deals with spotify request with link in request
        if 'open.spotify' in request:
            request = request.split(' ')
            link = None
            for word in request:
                if 'http' in word:
                    link = word
                    link = link.strip('\r')
                    link = link.strip('\n')
            if link is None:
                raise TrackNotFound
            track, artist, link = self.spot.get_track_info(url=link)

        # deals with youtube request with link in request
        elif 'https://www.youtube.com' in request or 'https://youtu.be/' in request:
            raise YoutubeLink

        # return none if link isn't spotify or youtube
        elif 'http' in request:
            raise UnsupportedLink

        # deals spotify request without link in request
        else:
            link = self.spot.search_song(request)
            if link is not None:
                track, artist, link = self.spot.get_track_info(url=link)
            else:
                raise TrackNotFound

        # returns track and artist if song was found, and adds song to queue if the request is a spotify request

        if self.db.is_track_in_queue(track, artist):
            raise TrackAlreadyInQueue

        self.db.add_to_queue(requester=user, track=track,
                             link=link, artist=artist)
        return track, artist
