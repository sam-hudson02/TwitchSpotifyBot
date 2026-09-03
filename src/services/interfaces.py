from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from discord import Embed
    from prisma.models import Queue as QueueModel
    from AudioController.track_info import TrackInfo
    from AudioController.track_context import TrackContext
    from twitch.message import Message
    from utils.types import Leaderboard


class SpotifyInterface(ABC):
    """A Spotify account: both its connection/authorization and playback."""

    # connection / authorization
    @abstractmethod
    def connect(self) -> bool:
        """Validate the cached token and record whether it worked."""

    @abstractmethod
    def is_connected(self) -> bool:
        ...

    @abstractmethod
    def verify(self) -> bool:
        """Make a live API call to confirm the credentials still work."""

    @abstractmethod
    def authorize_url(self, base_url: str) -> str:
        ...

    @abstractmethod
    def handle_callback(self, request_url: str) -> bool:
        ...

    # playback / queries
    @abstractmethod
    def search_song(self, query: str) -> str:
        ...

    @abstractmethod
    def get_track_info(self, url: str) -> 'TrackInfo':
        ...

    @abstractmethod
    def get_track_link(self, request: str) -> str:
        ...

    @abstractmethod
    def get_current_track(self) -> 'TrackInfo':
        ...

    @abstractmethod
    def get_recent_plays(self) -> list['TrackInfo']:
        ...

    @abstractmethod
    def get_context(self) -> 'TrackContext':
        ...

    @abstractmethod
    def get_queue(self) -> list[str]:
        ...

    @abstractmethod
    def add_to_queue(self, link: str) -> None:
        ...

    @abstractmethod
    def skip(self) -> 'TrackInfo':
        ...

    @abstractmethod
    def next(self) -> None:
        ...

    @abstractmethod
    def play(self, link: str) -> None:
        ...

    @abstractmethod
    def play_pause(self) -> bool:
        ...


class TwitchInterface(ABC):
    """The Twitch chat bot."""

    @abstractmethod
    async def start(self) -> None:
        ...

    @abstractmethod
    async def stop(self) -> None:
        ...

    @abstractmethod
    async def on_join(self, channel: str) -> None:
        ...

    @abstractmethod
    async def on_message(self, msg: 'Message') -> None:
        ...

    @abstractmethod
    async def on_live(self) -> None:
        ...

    @abstractmethod
    async def load_cogs(self) -> None:
        ...

    @abstractmethod
    async def on_error(self, msg: 'Message', error: Exception) -> None:
        ...

    @abstractmethod
    async def check_live(self) -> None:
        ...

    @abstractmethod
    async def start_routines(self) -> None:
        ...

    @abstractmethod
    async def skip(self) -> None:
        """Skip the current song, playing the next queued one if any."""

    @abstractmethod
    async def add_song(self, query: str, requester: str) -> 'TrackInfo':
        """Search for and add a song to the queue on behalf of a requester."""


class DiscordInterface(ABC):
    """The Discord webhook bot."""

    @abstractmethod
    async def start(self) -> bool:
        """Start the hook; return False if there is nothing to connect."""

    @abstractmethod
    async def stop(self) -> None:
        ...

    @abstractmethod
    def embed_queue(self, queue: list['QueueModel']) -> str:
        ...

    @abstractmethod
    async def embed_leaderboard(self, leaderboard: 'Leaderboard') -> 'Embed':
        ...

    @abstractmethod
    async def send_queue(self) -> None:
        ...

    @abstractmethod
    async def send_leaderboard(self) -> None:
        ...

    @abstractmethod
    async def check_queue(self) -> None:
        ...

    @abstractmethod
    async def check_leaderboard(self) -> None:
        ...

    @abstractmethod
    async def update(self) -> None:
        ...

    @abstractmethod
    async def cleanup(self) -> None:
        ...
