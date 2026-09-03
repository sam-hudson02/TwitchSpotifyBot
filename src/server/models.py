from pydantic import BaseModel


class TwitchStatus(BaseModel):
    running: bool
    channel: str
    bot_name: str | None = None
    live: bool | None = None
    active: bool | None = None


class DiscordStatus(BaseModel):
    connected: bool
    queue_webhook: bool
    leaderboard_webhook: bool


class SpotifyStatus(BaseModel):
    connected: bool
    working: bool
    user: str


class QueueItem(BaseModel):
    id: int
    position: float
    name: str
    artist: str
    requester: str
    url: str


class LeaderboardEntry(BaseModel):
    position: int
    username: str
    rates: int
    requests: int


class ControlResponse(BaseModel):
    service: str
    running: bool
    message: str


class NowPlaying(BaseModel):
    track: str | None = None
    artist: str | None = None
    requester: str | None = None
    album_art: str | None = None
    progress: int | None = None
    duration: int | None = None
    paused: bool = True
    playing_queue: bool = False
    live: bool = False


class QueueAdd(BaseModel):
    query: str


class QueueMove(BaseModel):
    after: int | None = None
