from utils.db_handler import DB
from utils.errors import TrackNotFound, TrackAlreadyInQueue, YoutubeLink, UnsupportedLink
from AudioController.spotify_api import Spotify
import time
from utils.async_timer import Timer
from utils import Log


class Context:
    def __init__(self) -> None:
        self.playlist = None
        self.progress = None
        self.duration = None
        self.album_art = None
        self.paused = True
        self.playing_queue = False
        self.track = None
        self.artist = None
        self.requester = None
        self.playback_id = None
        self.link = None
        self.active = True
        self.live = False

    def update(self, context: dict):
        if not self.playing_queue:
            self.playlist = context.get('playlist', None)
        self.progress = context.get('progress', None)
        self.duration = context.get('duration', None)
        self.album_art = context.get('album_art', None)
        self.paused = context.get('paused', True)
        self.track = context.get('track', None)
        self.artist = context.get('artist', None)
        if self.playback_id != context.get('playback_id', None):
            self.requester = None
            self.playing_queue = False
        self.playback_id = context.get('playback_id', None)

    def get_context(self):
        return {'playlist': self.playlist,
                'progress': self.progress,
                'duration': self.duration,
                'album_art': self.album_art,
                'paused': self.paused,
                'track': self.track,
                'artist': self.artist,
                'requester': self.requester,
                'playback_id': self.playback_id,
                'playing_queue': self.playing_queue,
                'active': self.active,
                'live': self.live}


class AudioController:
    def __init__(self, db: DB, spot: Spotify, ctx: Context, log: Log):
        self.db = db
        self.spot = spot
        self.log = log
        # Context is initialized in the main.py so that
        # it can be shared between twitch_bot and discord_bot
        self.context = ctx
        self.playlist = None
        self.next_timer = None
        self.timer_started = None
        self.context_time = None
        self.req_timer = None
        self.queue_blocked = False
        self.next = None
        self.history = []

    def add_to_queue(self, request: str, user: str):
        # deals with youtube request with link in request
        if 'https://www.youtube.com' in request or 'https://youtu.be/' in request:
            raise YoutubeLink

        words = request.split(' ')

        # deals with spotify request with link in request
        if 'open.spotify.com/track' in request:
            link = None
            for word in words:
                if 'http' in word:
                    link = word
                    link = link.strip('\r')
                    link = link.strip('\n')
            if link is None:
                raise TrackNotFound
            track, artist, link = self.spot.get_track_info(url=link)

        elif 'spotify:track:' in request:
            words = request.split(' ')
            link = None
            for word in words:
                if 'spotify:track:' in word:
                    link = word
                    link = link.strip('\r')
                    link = link.strip('\n')
            if link is None:
                raise TrackNotFound
            track, artist, link = self.spot.get_track_info(url=link)

        # raise error if link isn't spotify or youtube
        elif 'http' in request:
            raise UnsupportedLink

        # deals spotify request without link in request
        else:
            link = self.spot.search_song(request)
            if link is not None:
                track, artist, link = self.spot.get_track_info(url=link)
            else:
                raise TrackNotFound

        # returns track and artist if song was found,
        # and adds song to queue if the request is a spotify request

        if self.db.is_track_in_queue(track, artist):
            raise TrackAlreadyInQueue(track, artist)

        self.db.add_to_queue(requester=user, track=track,
                             link=link, artist=artist)
        return track, artist

    async def check_context(self):
        if self.context.paused:
            return
        if self.context.track is None:
            return
        if self.context_time is None:
            return
        if self.context.duration is None:
            return
        if self.context.progress is None:
            return

        time_since_context_update = time.time() * 1000 - self.context_time
        time_left = self.context.duration - \
            (self.context.progress + time_since_context_update)

        if time_left <= 9700 and time_left > 2100:
            if self.next_timer is not None:
                self.next_timer.cancel()
            self.next_timer = Timer(
                time_left - 2000, self.play_next, args=[False, time_left])
        return

    async def set_requester(self, track_info):
        track_name = track_info[2]
        current_playback_id = self.spot.get_context().get('playback_id', None)

        if current_playback_id is None:
            self.log.info('No current track.')
            return

        playback_id = track_info[5].split('/')[-1]
        if playback_id != current_playback_id:
            self.log.info('Playback ID does not match. ' +
                          f'{playback_id} != {current_playback_id}')
            return

        self.context.playback_id = playback_id
        self.context.requester = track_info[4]
        self.context.playing_queue = True
        self.log.info(f'Set requester to {track_info[4]} for {track_name}')

    def recheck_queue(self):
        if self.next is None:
            return

        if self.context.playback_id == self.next['id']:
            self.log.info(
                f'Playback ID matches next song in queue. {self.context.playback_id} == {self.next["id"]}')
            self.context.requester = self.next['requester']
            self.context.playing_queue = True
            self.queue_blocked = False
            return
        self.check_history()

    async def play_next(self, skipped: bool = False, time_left: int = 0):
        # check if any songs are in queue
        queue = self.db.get_queue()

        if self.req_timer is not None:
            self.req_timer.cancel()

        if len(queue) > 0:
            if self.queue_blocked:
                return
            # get next song in queue
            next_song = queue[0]
            # remove song from queue
            self.db.remove_from_queue_by_id(next_song[0])
            # play song
            # self.spot.sp.start_playback(uris=[next_song[5]])
            # update context
            self.log.info(f'Preparing to play {next_song[2]} ' +
                          f'requested by {next_song[4]}')
            self.spot.sp.add_to_queue(next_song[5])
            spot_queue = self.spot.get_queue()
            playback_id = next_song[5].split('/')[-1]
            if spot_queue[0] != playback_id:
                self.log.info('Playback position is not correct. ' +
                              f'{str(spot_queue[0])} != {playback_id}')
                self.queue_blocked = True
                self.next = {'id': playback_id, 'requester': next_song[4]}
            else:
                self.req_timer = Timer(
                    time_left + 3000, self.set_requester, args=[next_song])
            if skipped:
                self.spot.sp.next_track()
            self.add_to_history(playback_id, next_song[4])

        elif self.context.playing_queue:
            # if no songs are in queue, play the playlist
            self.context.playing_queue = False
            self.context.requester = None
            await self.update_context()

        elif skipped:
            self.spot.sp.next_track()
            await self.update_context()

        return

    def check_history(self):
        for song in self.history:
            if song['id'] == self.context.playback_id:
                self.context.requester = song['requester']
                self.context.playing_queue = True
                self.history.remove(song)
                self.log.info(f'Set requester to {song["requester"]} ' +
                              f'for {self.context.track}')
                return True
        return False

    def add_to_history(self, playback_id, requester):
        self.history.append({'id': playback_id, 'requester': requester})
        if len(self.history) > 10:
            self.history.pop(0)

    async def update_context(self):
        if not self.context.active:
            return
        if not self.context.live:
            return
        self.context_time = time.time() * 1000
        new_context = self.spot.get_context()
        if new_context is not None:
            self.context.update(new_context)
            await self.check_context()
            if self.queue_blocked:
                self.recheck_queue()
        else:
            self.context.track = None
            self.context.paused = True
