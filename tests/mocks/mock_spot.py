from AudioController.spotify_api import Spotify
from AudioController.track_context import TrackContext
from AudioController.track_info import TrackInfo
from utils.errors import BadLink, NoCurrentTrack, TrackNotFound


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
        self.current = None

    def search_song(self, query):
        print(f'Searching for {query}')
        song = self.song_map.get(query)
        if song is None:
            raise TrackNotFound
        print(f'Found {song}')
        return song

    def get_queue(self):
        return self.queue

    def get_context(self):
        info = self.current
        if info is None:
            raise NoCurrentTrack
        return TrackContext(info)

    def get_track_info(self, url):
        for name, link in self.song_map.items():
            if link == url:
                info = get_mock_json(name)
                return TrackInfo(info['item'])
        print(f'Could not find {url}')
        raise BadLink

    def set_progress(self, progress):
        if self.current is None:
            return
        self.current['progress_ms'] = progress

    def next(self):
        if len(self.queue) == 0:
            return
        url = self.queue.pop(0)
        name = url.split('/')[-1]
        self.current = get_mock_json(name)

    def add_to_queue(self, url):
        self.queue.append(url)
