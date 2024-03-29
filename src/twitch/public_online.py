import twitchio
from twitchio.ext import commands, routines
from utils.errors import *
from utils import Settings, DB, Log, Perms

class OnlineCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log: Log = bot.log
        self.db: DB = bot.db
        self.ac = bot.ac
        self.settings: Settings = bot.settings
        self.veto_votes = {'track': '', 'artist': '', 'votes': []}
        self.current_rates = {'track': '', 'artist': '', 'raters': []}
    
    async def cog_check(self, ctx: commands.Context) -> bool:
        if not self.settings.active:
            raise NotActive
        if not self.bot.is_live:
            return False
        return True

    @routines.routine(seconds=7.5)
    async def update_song_context(self):
        if not self.bot.is_live:
            return
        if not self.settings.active:
            return
        await self.ac.update_context()

    def _load_methods(self, bot) -> None:
        super()._load_methods(bot)
        self.cog_load()
    
    def cog_unload(self) -> None:
        self.log.info('Online cog unloaded')
        self.update_song_context.cancel()

    def cog_load(self) -> None:
        self.log.info('Online cog loaded')
        self.update_song_context.start()

    @commands.cooldown(1, 10, commands.Bucket.channel)
    @commands.command(name='sr')
    async def sr(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))

        await self.check_permission(ctx.author)

        if self.db.is_user_banned(user):
            raise UserBanned

        track, artist = self.ac.add_to_queue(request, user)

        if track is None:
            resp = f'Your request could not be found on spotify'
            await ctx.reply(resp)
            self.log.resp(resp)
            return False
        else:
            resp = f'{track} by {artist} has been added to the queue!'
            await ctx.reply(resp)
            self.log.resp(resp)
            self.db.add_requests(user)
            return True
    
    async def check_permission(self, user: twitchio.PartialChatter):
        perm: Perms = self.settings.permission
        if user.is_broadcaster:
            return
        if perm is Perms.SUBS:
            if not user.is_subscriber:
                raise BadPerms('subscriber')
        if perm is Perms.FOLLOWERS:
            if not await self.is_follower(user):
                raise BadPerms('follower')
        if perm is Perms.PRIVILEGED:
            if not await self.is_privileged(user):
                raise BadPerms('mod, subscriber or vip')

    async def is_follower(self, user: twitchio.PartialChatter):
        user = await user.user()
        following = await user.fetch_following()
        is_follower = self.bot.channel_name in [follow.to_user.name.lower() for follow in following]
        return is_follower

    async def is_privileged(self, user: twitchio.PartialChatter):
        if self.db.is_user_privileged(user.name.lower()):
            return True
        elif user.is_vip:
            return True
        elif user.is_mod:
            return True
        elif user.is_subscriber:
            return True
        else:
            return False

    @commands.command(name='song', aliases=['song-info'])
    async def song_info(self, ctx: commands.Context):
        if self.ac.context.track is None or self.ac.context.paused:
            resp = "No song currently playing!"

        elif self.ac.context.playing_queue:
            resp = f"Currently playing {self.ac.context.track} by {self.ac.context.artist} as requested by "\
                   f"@{self.ac.context.requester} !"
        else:
            resp = f"Currently playing {self.ac.context.track} by {self.ac.context.artist}!"

        await ctx.reply(resp)
        self.log.resp(resp)
        return None

    @commands.command(name='veto', aliases=['vote-skip'])
    async def veto(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        song_context = self.ac.context.get_context()

        resp, skip = self.add_veto(song_context, user)
        await ctx.reply(resp)
        self.log.resp(resp)
        if skip:
            self.ac.skip()

    def add_veto(self, song_context, user):
        if song_context is None:
            return None

        if (song_context['track'], song_context['artist']) != (self.veto_votes['track'], self.veto_votes['artist']):
            self.veto_votes['track'] = song_context['track']
            self.veto_votes['artist'] = song_context['artist']
            self.veto_votes['votes'] = []

        if user not in self.veto_votes['votes']:
            self.veto_votes['votes'].append(user)
        else:
            return f'You have already voted to veto the current song!', False

        votes = len(self.veto_votes['votes'])
        if votes >= self.settings.veto_pass:
            return f'{song_context["track"]} by {song_context["artist"]} has been vetoed by chat LUL', True
        else:
            return f'{votes} out of {self.settings.veto_pass} chatters have voted to skip the current song!', False

    @commands.command(name='rate', aliases=['like'])
    async def rate(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        song_context = self.ac.context.get_context()

        resp = self.add_rate(song_context, user)
        if resp is not None:
            await ctx.reply(resp)
            self.log.resp(resp)

    def add_rate(self, song_context, rater):
        if song_context is None:
            return None

        if not song_context['playing_queue']:
            return None

        # keeps record what user have rated current track so users can't rate current more than once
        if (song_context['track'], song_context['artist']) != (self.current_rates['track'],
                                                               self.current_rates['artist']):
            self.current_rates['track'] = song_context['track']
            self.current_rates['artist'] = song_context['artist']
            self.current_rates['raters'] = []

        if rater in self.current_rates['raters']:
            return None

        if song_context['requester'] == rater:
            return "Sorry, you can't rate your own requests LUL"
        else:
            self.db.add_rate(receiver=song_context['requester'], giver=rater)
            self.current_rates['raters'].append(rater)
            return f"@{rater} liked @{song_context['requester']}'s song request!"
    