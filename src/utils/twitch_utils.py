from prisma.models import User
from twitch.message import Chatter
from utils.errors import BadPerms, TimeNotFound, TargetNotFound
from typing import TYPE_CHECKING
from utils.settings import Perms, Settings
if TYPE_CHECKING:
    from AudioController.audio_controller import Context as SongContext
    from utils.db import DB


class VetoVotes:
    def __init__(self, song_context: 'SongContext') -> None:
        self.track = ''
        self.artist = ''
        self.votes = []
        self.ctx = song_context

    def user_voted(self, user: str) -> bool:
        self.check_track()
        return user in self.votes

    def add_vote(self, user: str) -> int:
        self.votes.append(user)
        return len(self.votes)

    def check_track(self) -> None:
        if (self.ctx.track, self.ctx.artist) == (self.track, self.artist):
            return
        self.track = self.ctx.track
        self.artist = self.ctx.artist
        self.votes = []


class RateTracker:
    def __init__(self, song_context: 'SongContext', db: 'DB') -> None:
        self.track = ''
        self.artist = ''
        self.requester = ''
        self.raters = []
        self.ctx = song_context
        self.db = db

    def user_rated(self, user: str) -> bool:
        self.check_track()
        return user in self.raters

    def check_track(self) -> None:
        if (self.ctx.track, self.ctx.artist) == (self.track, self.artist):
            return
        self.track = str(self.ctx.track)
        self.artist = str(self.ctx.artist)
        self.requester = str(self.ctx.requester)
        self.raters = []

    async def add_rate(self, giver: str) -> None:
        self.raters.append(giver)
        await self.db.add_rate(self.requester, giver)

    def is_requester(self, user: str) -> bool:
        return user == self.requester


def target_finder(request: str) -> str:
    words = request.split(' ')
    for word in words:
        if word.startswith('@'):
            target = word
            target = target.strip('@')
            target = target.strip('\n')
            target = target.strip('\r')
            target = target.strip(' ')
            return target
    raise TargetNotFound


def time_finder(request: str) -> dict:
    units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    for unit in units.keys():
        if unit in request:
            try:
                time = int(request.strip(unit))
            except ValueError:
                raise TimeNotFound
            return {'time': time, 'unit': unit}
    # if no unit is found, default to minutes
    unit = 'm'
    request = request.strip(unit)
    try:
        time = int(request)
    except ValueError:
        raise TimeNotFound
    return {'time': time, 'unit': unit}


async def is_privileged(chatter: Chatter, user: User):
    if user.mod or user.admin:
        return True
    elif chatter.is_vip:
        return True
    elif chatter.is_mod:
        return True
    elif chatter.is_subscriber:
        return True
    else:
        return False


async def check_permission(settings: Settings, chatter: Chatter, user: User):
    perm: Perms = settings.permission
    if chatter.is_broadcaster:
        return
    if perm is Perms.SUBS:
        if not chatter.is_subscriber:
            raise BadPerms('subscriber')
    if perm is Perms.FOLLOWERS:
        if not await chatter.is_follower():
            raise BadPerms('follower')
    if perm is Perms.PRIVILEGED:
        if not await is_privileged(chatter, user):
            raise BadPerms('mod, subscriber or vip')
