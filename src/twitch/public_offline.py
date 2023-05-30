from twitch.cog import Cog
from utils import Settings, DB, Perms
from typing import TYPE_CHECKING
from twitch.router import Context
if TYPE_CHECKING:
    from twitch.bot import Bot as TwitchBot


class OfflineCog(Cog):
    def __init__(self, bot: 'TwitchBot'):
        super().__init__(bot)
        self.bot = bot
        self.settings: Settings = bot.settings
        self.db: DB = bot.db

    async def load(self):
        self.bot.router.add_route('help', self.help)
        self.bot.router.add_route('sr-status', self.sp_status)
        self.bot.router.add_route('leader', self.leader)
        self.bot.router.add_route('stats', self.stats)

    async def help(self, ctx: Context):
        await ctx.reply('A list of commands can be found here: '
                        'https://github.com/sam-hudson02/TwitchSpotifyBot/blob/main/Commands.md')

    async def sp_status(self, ctx: Context):
        if self.settings.active:
            if self.bot.ac.context.live:
                resp = self.get_perm_resp()
            else:
                resp = "Song request are turned on but won't be taken till "
                f"{self.bot.channel} is live."
        else:
            resp = 'Song request are turned off.'
        await ctx.reply(resp)

    def get_perm_resp(self):
        if self.settings.permission is Perms.ALL:
            return 'Song request are turned on!'
        elif self.settings.permission is Perms.FOLLOWERS:
            return 'Song request are turned on for followers only!'
        elif self.settings.permission is Perms.SUBS:
            return 'Song request are turned on for subs only!'
        elif self.settings.permission is Perms.PRIVILEGED:
            return 'Song request are turned on for privileged users only!'
        else:
            return 'Song request are turned on!'

    async def leader(self, ctx: Context):
        leader = await self.db.get_leader()
        if leader is None:
            resp = "No one has been rated yet!"
        else:
            resp = f"Current leader is @{leader.username} with {leader.rates}"
            "rates!"

        await ctx.reply(resp)

    async def stats(self, ctx: Context):
        position = await self.db.get_user_position(ctx.user.username,
                                                   user=ctx.user)

        await ctx.reply(f"Your position is {position} with "
                        f"{ctx.user.rates} rates from {ctx.user.requests} "
                        f"requests and {ctx.user.ratesGiven} rates given!")

    async def ping(self, ctx: Context):
        resp = 'Pong!'
        await ctx.reply(resp)
