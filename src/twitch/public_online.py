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
        self.veto_votes = VetoVotes(self.ac.context)
        self.rate_tracker = RateTracker(self.ac.context, self.db)

    async def load(self):
        self.bot.router.add_route('sr', self.sr, self)
        self.bot.router.add_route('song', self.song_info, self)
        self.bot.router.add_route('rm', self.remove_request, self)
        self.bot.router.add_route('next', self.next_song, self)
        self.bot.router.add_route('veto', self.veto, self)
        self.bot.router.add_route('rate', self.rate, self)

    async def on_error(self, msg: Message, error: Exception):
        if isinstance(error, YoutubeLink):
            await msg.reply('Please use a youtube link!')
        elif isinstance(error, UserBanned):
            await msg.reply('You are banned from requesting songs!')
        elif isinstance(error, TrackNotFound) or isinstance(error, BadLink):
            await msg.reply('Sorry, I could not find that song!')
        elif isinstance(error, BadPerms):
            await msg.reply(f'Only {error.perm} can use this command at the \
                              moment!')
        elif isinstance(error, TrackAlreadyInQueue):
            await msg.reply('That song is already in the queue!')
        else:
            raise error

    async def before_invoke(self, ctx: Context) -> bool:
        if not self.settings.active:
            await ctx.reply('This command is currently disabled!')
            return False
        if not self.ac.context.live:
            await ctx.reply('This command can only be used while live!')
            return False
        return True

    async def update_song_context(self):
        print('updating song context')
        if not self.ac.context.live:
            print('not live')
            return
        if not self.settings.active:
            print('not active')
            return
        await self.ac.update_context()

    async def sr(self, ctx: Context):
        await check_permission(self.settings, ctx.chatter, ctx.user)

        if ctx.user.ban:
            raise UserBanned

        info = await self.ac.add_to_queue(ctx.content, ctx.user.username)
        await ctx.reply(f'{info.track} by {info.artist} has been added to \
                          the queue!')

    async def song_info(self, ctx: Context):
        print('song called')
        if self.ac.context.track is None or self.ac.context.paused:
            await ctx.reply("No song currently playing!")

        elif self.ac.context.playing_queue:
            await ctx.reply(f"Currently playing "
                            f"{self.ac.context.track} by "
                            f"{self.ac.context.artist} as requested by "
                            f"@{self.ac.context.requester} !")
        else:
            await ctx.reply(f"Currently playing "
                            f"{self.ac.context.track} by "
                            f"{self.ac.context.artist}!")

    async def next_song(self, ctx: Context):
        next_song = await self.db.get_next_song()
        if next_song is None:
            await ctx.reply('No songs in queue!')
            return
        await ctx.reply(f'Next song is {next_song.name} by '
                        f'{next_song.artist} as requested by '
                        f'{next_song.requester}!')

    async def remove_request(self, ctx: Context):
        req = await self.bot.db.remove_last_request(ctx.user.username)
        if req is None:
            await ctx.reply('You have no requests in the queue!')
        else:
            await ctx.reply(f'Your last request, {req.name} by {req.artist}, '
                            f'has been removed from the queue!')

    async def veto(self, ctx: Context):
        if self.veto_votes.user_voted(ctx.user.username):
            await ctx.reply('You have already voted to veto the current song!')
            return
        votes = self.veto_votes.add_vote(ctx.user.username)
        if votes >= self.settings.veto_pass:
            await ctx.reply(f'{self.ac.context.track} by '
                            f'{self.ac.context.artist} has been vetoed by chat'
                            ' LUL')
            await self.ac.play_next(skipped=True)
        else:
            await ctx.reply(f'{votes} out of {self.settings.veto_pass} '
                            'chatters have voted to skip the current song!')

    async def rate(self, ctx: Context):
        if self.rate_tracker.user_rated(ctx.user.username):
            await ctx.reply('You have already rated this song!')
            return

        if self.rate_tracker.is_requester(ctx.user.username):
            await ctx.reply('You cannot rate your own song! LUL')
            return

        await self.rate_tracker.add_rate(ctx.user.username)
        await ctx.reply(f'@{ctx.user.username} has rated '
                        f'@{self.ac.context.requester}\'s song ')
