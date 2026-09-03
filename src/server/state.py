import asyncio
from typing import Callable

from utils import Log, Creds, init_dirs, Settings, DB
from AudioController.audio_controller import Context
from AudioController.spotify_api import Spotify
from services import Services, TwitchInterface, DiscordInterface
from server.queue_socket import QueueSocket
from twitch.bot import Bot
from disc.webhook import DiscordHook

TwitchFactory = Callable[[Services], TwitchInterface]
DiscordFactory = Callable[[Services], DiscordInterface]


class AppState:
    """Owns the shared Services and each bot's lifecycle.

    The bots are built from an injected `Services` via injected factories, so
    tests supply a Services of mocks and mock factories. Twitch and Discord are
    independent: either can be started or stopped without the other. Everything
    runs on uvicorn's event loop; blocking spotipy calls are pushed to a worker
    thread. Start-up is best-effort: a bad token or web error is logged and
    reported, never allowed to crash the server."""

    def __init__(self, *, log: Log, services: Services,
                 twitch_factory: TwitchFactory,
                 discord_factory: DiscordFactory):
        self.log = log
        self.services = services
        self._twitch_factory = twitch_factory
        self._discord_factory = discord_factory
        self.twitch: TwitchInterface | None = None
        self.discord: DiscordInterface | None = None
        self.queue_socket = QueueSocket(self.queue_snapshot)

    @classmethod
    def create(cls) -> 'AppState':
        init_dirs()
        log = Log('server', file='./data/server.log')
        creds = Creds(log)
        services = Services(creds=creds,
                            settings=Settings(),
                            db=DB(),
                            spotify=Spotify(creds.spotify),
                            context=Context())
        return cls(log=log, services=services,
                   twitch_factory=Bot, discord_factory=DiscordHook)

    # convenience accessors for the routes
    @property
    def creds(self) -> Creds:
        return self.services.creds

    @property
    def spotify(self):
        return self.services.spotify

    @property
    def db(self) -> DB:
        return self.services.db

    @property
    def twitch_running(self) -> bool:
        return self.twitch is not None

    @property
    def discord_running(self) -> bool:
        return self.discord is not None

    async def startup(self) -> None:
        await self.services.db.connect()
        # spotipy is blocking, so validate the cached token off the event loop
        await asyncio.to_thread(self.services.spotify.connect)
        # autostart is best-effort; failures are logged and the server still
        # comes up so the control endpoints can retry
        if self.services.spotify.is_connected():
            await self.start_twitch()
        await self.start_discord()

    async def shutdown(self) -> None:
        await self.stop_twitch()
        await self.stop_discord()
        await self.services.db.disconnect()

    async def start_twitch(self) -> tuple[bool, str]:
        if self.twitch is not None:
            return True, 'already running'
        if not self.services.spotify.is_connected():
            return False, 'Spotify is not connected'
        try:
            twitch = self._twitch_factory(self.services)
            await twitch.start()
        except Exception as e:
            self.log.error(f'Failed to start Twitch bot: {e}')
            return False, f'Twitch bot could not start: {e}'
        self.twitch = twitch
        return True, 'started'

    async def stop_twitch(self) -> tuple[bool, str]:
        if self.twitch is None:
            return True, 'not running'
        try:
            await self.twitch.stop()
        except Exception as e:
            self.log.error(f'Error stopping Twitch bot: {e}')
        self.twitch = None
        return True, 'stopped'

    async def start_discord(self) -> tuple[bool, str]:
        if self.discord is not None:
            return True, 'already running'
        creds = self.services.creds.discord
        if not (creds.queue_webhook or creds.leaderboard_webhook):
            return False, 'No Discord webhooks configured'
        try:
            discord = self._discord_factory(self.services)
            started = await discord.start()
        except Exception as e:
            self.log.error(f'Failed to start Discord hook: {e}')
            return False, f'Discord hook could not start: {e}'
        if not started:
            await discord.stop()
            return False, 'Discord hook failed to start'
        self.discord = discord
        return True, 'started'

    async def stop_discord(self) -> tuple[bool, str]:
        if self.discord is None:
            return True, 'not running'
        try:
            await self.discord.stop()
        except Exception as e:
            self.log.error(f'Error stopping Discord hook: {e}')
        self.discord = None
        return True, 'stopped'

    # playback -----------------------------------------------------------

    def now_playing(self) -> dict:
        """The bot's current playback context (kept fresh by the update loop
        while the Twitch bot runs); values are last-known when it is stopped."""
        return self.services.context.get_context()

    async def skip(self) -> None:
        """Skip the current song. Requires the Twitch bot (it owns the
        queue-aware audio controller); callers guard `twitch_running`."""
        await self.twitch.skip()
        await self.queue_socket.broadcast_queue()

    async def queue_add(self, query: str):
        """Add a song to the queue as the broadcaster. Requires the Twitch bot;
        callers guard `twitch_running`."""
        requester = self.services.creds.twitch.channel
        info = await self.twitch.add_song(query, requester)
        await self.queue_socket.broadcast_queue()
        return info

    # queue --------------------------------------------------------------

    async def queue_snapshot(self) -> list[dict]:
        return [{'id': q.id,
                 'position': q.position,
                 'name': q.songName,
                 'artist': q.artist,
                 'requester': q.requester,
                 'url': q.url}
                for q in await self.services.db.get_queue()]

    async def queue_move(self, req_id: int, after: int | None) -> None:
        """Move a queue entry to just after `after` (or to the front if None),
        assigning a fractional position between its new neighbours."""
        rows = await self.services.db.get_queue()
        if req_id not in {r.id for r in rows}:
            raise ValueError(f'unknown queue id {req_id}')
        others = [r for r in rows if r.id != req_id]

        if after is None:
            new_pos = (others[0].position - 1) if others else 0.0
        else:
            idx = next((i for i, r in enumerate(others) if r.id == after), None)
            if idx is None:
                raise ValueError(f'unknown queue id {after}')
            prev_pos = others[idx].position
            next_pos = others[idx + 1].position if idx + 1 < len(others) \
                else prev_pos + 1
            new_pos = (prev_pos + next_pos) / 2

        await self.services.db.set_position(req_id, new_pos)
        await self.queue_socket.broadcast_queue()

    async def queue_remove(self, req_id: int) -> None:
        await self.services.db.remove_from_queue(req_id)
        await self.queue_socket.broadcast_queue()

    async def queue_clear(self) -> None:
        await self.services.db.clear_queue()
        await self.queue_socket.broadcast_queue()
