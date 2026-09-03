from AudioController.audio_controller import AudioController
from twitch.message import Message
from utils.errors import BadLink, BadPerms, TrackAlreadyInQueue, TrackNotFound, UserBanned, YoutubeLink
from utils import Settings, DB, VetoVotes, RateTracker
from typing import TYPE_CHECKING
from twitch.cog import Cog
from twitch.router import Context
from utils.twitch_utils import check_permission
if TYPE_CHECKING:
    from twitch.bot import Bot as TwitchBot


class OnlineCog(Cog):
    def __init__(self, bot: 'TwitchBot'):
        super().__init__(bot)
        self.bot = bot
        self.db: DB = bot.db
        self.ac: AudioController = bot.ac
        self.settings: Settings = bot.settings
        self.commands = bot.commands
        self.veto_votes = VetoVotes(self.ac.context)
        self.rate_tracker = RateTracker(self.ac.context, self.db)

    async def load(self):
        self.register('SONG_REQUEST', self.sr)
        self.register('SONG', self.song_info)
        self.register('REMOVE', self.remove_request)
        self.register('NEXT', self.next_song)
        self.register('VETO', self.veto)
        self.register('RATE', self.rate)

    async def on_error(self, msg: Message, error: Exception):
        if isinstance(error, YoutubeLink):
            await msg.reply(self.commands.message('SONG_REQUEST', 'youtube_link'))
        elif isinstance(error, UserBanned):
            await msg.reply(self.commands.message('SONG_REQUEST', 'banned'))
        elif isinstance(error, TrackNotFound) or isinstance(error, BadLink):
            await msg.reply(self.commands.message('SONG_REQUEST', 'not_found'))
        elif isinstance(error, BadPerms):
            await msg.reply(self.commands.message('SONG_REQUEST', 'bad_perms',
                                                  perm=error.perm))
        elif isinstance(error, TrackAlreadyInQueue):
            await msg.reply(self.commands.message('SONG_REQUEST',
                                                  'already_in_queue'))
        else:
            raise error

    async def before_invoke(self, ctx: Context) -> bool:
        if not self.settings.active:
            await ctx.reply(self.commands.message('SONG_REQUEST', 'disabled'))
            return False
        if not self.ac.context.live:
            await ctx.reply(self.commands.message('SONG_REQUEST', 'not_live'))
            return False
        return True

    async def update_song_context(self):
        if not self.ac.context.live:
            return
        if not self.settings.active:
            return
        await self.ac.update_context()

    async def sr(self, ctx: Context):
        await check_permission(self.settings, ctx.chatter, ctx.user)

        if ctx.user.ban:
            raise UserBanned

        info = await self.ac.add_to_queue(ctx.content, ctx.user.username)
        await ctx.reply(self.commands.message('SONG_REQUEST', 'added',
                                              song=info.track,
                                              artist=info.artist))

    async def song_info(self, ctx: Context):
        if self.ac.context.track is None or self.ac.context.paused:
            await ctx.reply(self.commands.message('SONG', 'not_playing'))
        elif self.ac.context.playing_queue:
            await ctx.reply(self.commands.message(
                'SONG', 'playing_queue', song=self.ac.context.track,
                artist=self.ac.context.artist,
                requester=self.ac.context.requester))
        else:
            await ctx.reply(self.commands.message(
                'SONG', 'playing', song=self.ac.context.track,
                artist=self.ac.context.artist))

    async def next_song(self, ctx: Context):
        next_song = await self.db.get_next_song()
        if next_song is None:
            await ctx.reply(self.commands.message('NEXT', 'empty'))
            return
        await ctx.reply(self.commands.message('NEXT', 'next',
                                              song=next_song.songName,
                                              artist=next_song.artist,
                                              requester=next_song.requester))

    async def remove_request(self, ctx: Context):
        req = await self.bot.db.remove_last_request(ctx.user.username)
        if req is None:
            await ctx.reply(self.commands.message('REMOVE', 'no_requests'))
        else:
            await ctx.reply(self.commands.message('REMOVE', 'removed',
                                                  song=req.songName,
                                                  artist=req.artist))

    async def veto(self, ctx: Context):
        if self.veto_votes.user_voted(ctx.user.username):
            await ctx.reply(self.commands.message('VETO', 'already_voted'))
            return
        votes = self.veto_votes.add_vote(ctx.user.username)
        if votes >= self.settings.veto_pass:
            await ctx.reply(self.commands.message(
                'VETO', 'vetoed', song=self.ac.context.track,
                artist=self.ac.context.artist))
            await self.ac.play_next(skipped=True)
        else:
            await ctx.reply(self.commands.message(
                'VETO', 'voted', votes=votes,
                veto_pass=self.settings.veto_pass))

    async def rate(self, ctx: Context):
        if self.rate_tracker.user_rated(ctx.user.username):
            await ctx.reply(self.commands.message('RATE', 'already_rated'))
            return

        if self.rate_tracker.is_requester(ctx.user.username):
            await ctx.reply(self.commands.message('RATE', 'own_song'))
            return

        await self.rate_tracker.add_rate(ctx.user.username)
        await ctx.send(self.commands.message(
            'RATE', 'rated', user=ctx.user.username,
            requester=self.ac.context.requester))
