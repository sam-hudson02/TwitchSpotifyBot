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
        self.commands = bot.commands

    async def load(self):
        self.register('HELP', self.help)
        self.register('SR_STATUS', self.sp_status)
        self.register('LEADER', self.leader)
        self.register('STATS', self.stats)

    async def help(self, ctx: Context):
        await ctx.reply(self.commands.message('HELP', 'help'))

    async def sp_status(self, ctx: Context):
        if self.settings.active:
            if self.bot.ac.context.live:
                resp = self.get_perm_resp()
            else:
                resp = self.commands.message('SR_STATUS', 'on_not_live',
                                             channel=self.bot.channel)
        else:
            resp = self.commands.message('SR_STATUS', 'off')
        await ctx.reply(resp)

    def get_perm_resp(self):
        if self.settings.permission is Perms.FOLLOWERS:
            return self.commands.message('SR_STATUS', 'on_followers')
        elif self.settings.permission is Perms.SUBS:
            return self.commands.message('SR_STATUS', 'on_subs')
        elif self.settings.permission is Perms.PRIVILEGED:
            return self.commands.message('SR_STATUS', 'on_privileged')
        else:
            return self.commands.message('SR_STATUS', 'on')

    async def leader(self, ctx: Context):
        leader = await self.db.get_leader()
        if leader is None:
            resp = self.commands.message('LEADER', 'none')
        else:
            resp = self.commands.message('LEADER', 'leader',
                                         user=leader.username,
                                         rates=leader.rates)
        await ctx.reply(resp)

    async def stats(self, ctx: Context):
        position = await self.db.get_user_position(ctx.user.username,
                                                   user=ctx.user)
        await ctx.reply(self.commands.message(
            'STATS', 'stats', position=position, rates=ctx.user.rates,
            requests=ctx.user.requests, rates_given=ctx.user.ratesGiven))

    async def ping(self, ctx: Context):
        resp = 'Pong!'
        await ctx.reply(resp)
