from types import SimpleNamespace

from services import Services


class MockSpotify:
    def __init__(self, connected=True):
        self._connected = connected

    def connect(self):
        return self._connected

    def is_connected(self):
        return self._connected

    def verify(self):
        return self._connected


class MockTwitchBot:
    def __init__(self, services=None, start_ok=True):
        self.started = False
        self.stopped = False
        self.skipped = False
        self.added = None
        self.running = False
        self._start_ok = start_ok
        self.context = SimpleNamespace(live=True, active=True)

    async def start(self):
        if not self._start_ok:
            raise RuntimeError('bad token')
        self.started = True
        self.running = True

    async def stop(self):
        self.stopped = True
        self.running = False

    async def skip(self):
        self.skipped = True

    async def add_song(self, query, requester):
        self.added = (query, requester)
        return SimpleNamespace(track=query, artist='artist', link='http://track')


class MockDiscordBot:
    def __init__(self, services=None, start_ok=True):
        self.started = False
        self.stopped = False
        self._start_ok = start_ok

    async def start(self):
        self.started = self._start_ok
        return self._start_ok

    async def stop(self):
        self.stopped = True


class MockDB:
    def __init__(self):
        self.connected = False

    async def connect(self):
        self.connected = True

    async def disconnect(self):
        self.connected = False


def queue_row(id, position, name='song', artist='artist', requester='user',
              url='http://track'):
    return SimpleNamespace(id=id, position=position, songName=name,
                           artist=artist, requester=requester, url=url)


class MockQueueDB(MockDB):
    def __init__(self, rows=None):
        super().__init__()
        self.rows = list(rows) if rows else []

    async def get_queue(self):
        return sorted(self.rows, key=lambda r: r.position)

    async def set_position(self, req_id, position):
        for r in self.rows:
            if r.id == req_id:
                r.position = position

    async def remove_from_queue(self, req_id):
        self.rows = [r for r in self.rows if r.id != req_id]

    async def clear_queue(self):
        self.rows = []


def user_row(username, ban=False, dj=False, admin=False, requests=0, rates=0):
    return SimpleNamespace(username=username, ban=ban, dj=dj, admin=admin,
                           requests=requests, rates=rates, ratesGiven=0)


class MockUserDB(MockDB):
    def __init__(self, users=None):
        super().__init__()
        self.users = {u.username: u for u in (users or [])}

    async def get_user(self, username, admin=False, dj=False):
        if username not in self.users:
            self.users[username] = user_row(username, admin=admin, dj=dj)
        return self.users[username]

    async def get_all_users(self):
        return list(self.users.values())

    async def ban_user(self, username):
        (await self.get_user(username)).ban = True

    async def unban_user(self, username):
        (await self.get_user(username)).ban = False

    async def dj_user(self, username):
        (await self.get_user(username)).dj = True

    async def undj_user(self, username):
        (await self.get_user(username)).dj = False


def mock_creds(channel='chan', bot_name='bot', queue_webhook='http://queue',
               leaderboard_webhook=None, server_token='token'):
    return SimpleNamespace(
        twitch=SimpleNamespace(channel=channel, bot_name=bot_name,
                               access_token='at', refresh_token='rt'),
        discord=SimpleNamespace(queue_webhook=queue_webhook,
                                leaderboard_webhook=leaderboard_webhook),
        spotify=SimpleNamespace(username='user', client_id='cid',
                                client_secret='sec'),
        server_token=server_token,
    )


def mock_services(spotify=None, creds=None, db=None):
    return Services(
        creds=creds or mock_creds(),
        settings=object(),
        db=db or MockDB(),
        spotify=spotify or MockSpotify(),
        context=object(),
    )
