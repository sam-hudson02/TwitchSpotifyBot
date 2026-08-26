from AudioController.spotify_api import Spotify
from AudioController.track_context import TrackContext
from AudioController.track_info import TrackInfo
from utils.errors import BadLink, NoCurrentTrack, TrackNotFound
from utils.logger import Log


def get_mock_json(name='test') -> dict:
    info = {
        'item': {
            'name': name,
            'artists': [
                {
                    'name': name
                }
            ],
            'duration_ms': 10000,
            'album': {
                'images': [
                    {
                        'url': name
                    }
                ]
            },
            'id': name,
            'external_urls': {
                'spotify': f'https://open.spotify.com/track/{name}'
            },
        },
        'context': {
            'external_urls': {
                'spotify': f'https://open.spotify.com/playlist/{name}'
            },
        },
        'progress_ms': 0,
        'is_playing': True
    }
    return info


class MockSpot(Spotify):
    def __init__(self):
        self.song_map = {
            'test': 'https://open.spotify.com/track/test',
            'test2': 'https://open.spotify.com/track/test2',
            'test3': 'https://open.spotify.com/track/test3',
        }
        self.queue = []
        self.current = self.init_current()
        self.log = Log('Spotify')

    def init_current(self):
        json = get_mock_json('test3')
        return json

    def search_song(self, query):
        self.log.info(f'Searching for {query}')
        song = self.song_map.get(query)
        if song is None:
            raise TrackNotFound
        self.log.info(f'Found {song}')
        return song

    def get_queue(self):
        return self.queue

    def get_context(self):
        info = self.current
        if info is None:
            self.log.error('No current track')
            raise NoCurrentTrack
        return TrackContext(info)

    def set_current(self, name):
        self.log.info(f'Setting current to {name}')
        self.current = get_mock_json(name)

    def get_track_info(self, url):
        for name, link in self.song_map.items():
            if link == url:
                info = get_mock_json(name)
                self.log.info(f'Found {url}')
                return TrackInfo(info['item'])
        self.log.error(f'Could not find {url}')
        raise BadLink

    def set_progress(self, progress):
        self.log.info(f'Setting progress to {progress}')
        if self.current is None:
            return
        self.current['progress_ms'] = progress

    def next(self):
        self.log.info('Skipping to next track')
        if len(self.queue) == 0:
            return
        url = self.queue.pop(0)
        name = url.split('/')[-1]
        self.current = get_mock_json(name)

    def add_to_queue(self, url):
        name = url.split('/')[-1]
        self.log.info(f'Adding {name} to queue')
        self.queue.append(name)
