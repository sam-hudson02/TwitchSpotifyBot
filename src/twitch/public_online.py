from prisma.models import User
import twitchio
from twitchio.ext import commands, routines
from AudioController.audio_controller import AudioController
from utils.errors import NotActive, BadPerms, UserBanned
from utils import Settings, DB, Log, Perms, get_username, get_message


class OnlineCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log: Log = bot.log
        self.db: DB = bot.db
        self.ac: AudioController = bot.ac
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
        print('updating song context')
        if not self.bot.is_live:
            print('not live')
            return
        if not self.settings.active:
            print('not active')
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
        print('starting update song context')
        self.update_song_context.start()
        print('finished update song context')

    @commands.cooldown(1, 10, commands.Bucket.channel)
    @commands.command(name='sr')
    async def sr(self, ctx: commands.Context):
        username = get_username(ctx)
        request = get_message(ctx)
        user = await self.db.get_user(username)

        chatter = ctx.author
        await self.check_permission(chatter, user)

        if user.ban:
            raise UserBanned

        track, artist = await self.ac.add_to_queue(request, username)

        if track is None:
            await self.bot.reply(ctx, 'Your request could not be found on '
                                 'spotify')
            return False
        else:
            await self.bot.reply(ctx, f'{track} by {artist} has been added to the '
                                 'queue!')
            return True

    async def check_permission(self, chatter: twitchio.Chatter, user: User):
        perm: Perms = self.settings.permission
        if chatter.is_broadcaster:
            return
        if perm is Perms.SUBS:
            if not chatter.is_subscriber:
                raise BadPerms('subscriber')
        if perm is Perms.FOLLOWERS:
            if not await self.is_follower(chatter):
                raise BadPerms('follower')
        if perm is Perms.PRIVILEGED:
            if not await self.is_privileged(chatter, user):
                raise BadPerms('mod, subscriber or vip')

    async def is_follower(self, chatter: twitchio.Chatter):
        user = await chatter.user()
        following = await user.fetch_following()
        is_follower = self.bot.channel_name in [
            follow.to_user.name.lower() for follow in following]
        return is_follower

    async def is_privileged(self, chatter: twitchio.Chatter, user: User):
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

    @commands.command(name='song', aliases=['song-info'])
    async def song_info(self, ctx: commands.Context):
        if self.ac.context.track is None or self.ac.context.paused:
            await self.bot.reply(ctx, "No song currently playing!")

        elif self.ac.context.playing_queue:
            await self.bot.reply(ctx, f"Currently playing "
                                 f"{self.ac.context.track} by "
                                 f"{self.ac.context.artist} as requested by "
                                 f"@{self.ac.context.requester} !")
        else:
            await self.bot.reply(ctx, f"Currently playing "
                                 f"{self.ac.context.track} by "
                                 f"{self.ac.context.artist}!")

    @commands.command(name='sp-next', aliases=['next'])
    async def next_song(self, ctx: commands.Context):
        next_song = await self.db.get_next_song()
        if next_song is None:
            await self.bot.reply(ctx, 'No songs in queue!')
            return
        await self.bot.reply(ctx, f'Next song is {next_song.name} by '
                             f'{next_song.artist} as requested by '
                             f'{next_song.requester}!')

    @ commands.command(name='veto', aliases=['vote-skip'])
    async def veto(self, ctx: commands.Context):
        username = get_username(ctx)
        song_context = self.ac.context.get_context()

        resp, skip = self.add_veto(song_context, username)
        if resp is None:
            return

        await self.bot.reply(ctx, resp)
        if skip:
            await self.ac.play_next(skipped=True)

    def add_veto(self, song_context, user):
        if song_context is None:
            return None, False

        if (song_context['track'], song_context['artist']) != (self.veto_votes['track'], self.veto_votes['artist']):
            self.veto_votes['track'] = song_context['track']
            self.veto_votes['artist'] = song_context['artist']
            self.veto_votes['votes'] = []

        if user not in self.veto_votes['votes']:
            self.veto_votes['votes'].append(user)
        else:
            return 'You have already voted to veto the current song!', False

        votes = len(self.veto_votes['votes'])
        if votes >= self.settings.veto_pass:
            return f'{song_context["track"]} by {song_context["artist"]} has been vetoed by chat LUL', True
        else:
            return f'{votes} out of {self.settings.veto_pass} chatters have voted to skip the current song!', False

    @ commands.command(name='rate', aliases=['like'])
    async def rate(self, ctx: commands.Context):
        username = get_username(ctx)

        resp = await self.add_rate(username)
        if resp is not None:
            await self.bot.reply(ctx, resp)

    async def add_rate(self, rater):
        song_context = self.ac.context
        if not song_context['playing_queue']:
            return None

        # keeps record what user have rated current track so users can't rate current more than once
        if (song_context.track, song_context.artist) != (self.current_rates['track'],
                                                         self.current_rates['artist']):
            self.current_rates['track'] = song_context.track
            self.current_rates['artist'] = song_context.artist
            self.current_rates['raters'] = []

        if rater in self.current_rates['raters']:
            return None

        if song_context.requester == rater:
            return "Sorry, you can't rate your own requests LUL"
        else:
            await self.db.add_rate(receiver=song_context.requester,
                                   giver=rater)
            self.current_rates['raters'].append(rater)
            return f"@{rater} liked @{song_context.requester}'s song request!"
