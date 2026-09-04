from prisma.models import User
from utils.errors import NotAuthorized, NotActive
from utils import target_finder, Settings, DB, Perms
from utils.twitch_utils import is_moderator
from twitch.cog import Cog
from twitch.router import Context
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from twitch.bot import Bot as TwitchBot


class ModCog(Cog):
    def __init__(self, bot: 'TwitchBot'):
        self.bot = bot
        self.db: DB = bot.db
        self.ac = bot.ac
        self.settings: Settings = bot.settings
        self.channel = bot.channel
        self.commands = bot.commands

    async def load(self):
        self.register('SKIP', self.skip)
        self.register('BAN', self.ban_command)
        self.register('UNBAN', self.unban_command)
        self.register('FOLLOWERS_ONLY', self.followers_only)
        self.register('SUBS_ONLY', self.subs_only)
        self.register('PRIV_ONLY', self.privileged_only)
        self.register('DJS_ONLY', self.djs_only)
        self.register('ALL', self.all_perms)

    async def before_invoke(self, ctx: Context) -> bool:
        if not await is_moderator(ctx.chatter, ctx.user):
            raise NotAuthorized('mod')
        return True

    async def skip(self, ctx: Context):
        if not self.settings.active or self.ac.context.paused:
            raise NotActive
        if not self.ac.context.live:
            await ctx.reply(self.commands.message('SKIP', 'not_live',
                                                  channel=self.channel))
            return

        await self.ac.play_next(skipped=True)
        await ctx.reply(self.commands.message('SKIP', 'skipping'))

    async def ban_command(self, ctx: Context):
        target_username = target_finder(ctx.content)
        target = await self.db.get_user(target_username)

        if await self.ban(target):
            await ctx.reply(self.commands.message('BAN', 'banned',
                                                  target=target_username))

    async def ban(self, target: User):
        # anyone who reached here is a moderator; only admins are protected
        if target.admin:
            return False
        await self.db.ban_user(target.username)
        return True

    async def unban_command(self, ctx: Context):
        target_username = target_finder(ctx.content)
        await self.db.unban_user(target_username)
        await ctx.reply(self.commands.message('UNBAN', 'unbanned',
                                              target=target_username))

    async def followers_only(self, ctx: Context):
        self.settings.set_permission(Perms.FOLLOWERS)
        await ctx.reply(self.commands.message('FOLLOWERS_ONLY', 'set'))

    async def subs_only(self, ctx: Context):
        self.settings.set_permission(Perms.SUBS)
        await ctx.reply(self.commands.message('SUBS_ONLY', 'set'))

    async def privileged_only(self, ctx: Context):
        self.settings.set_permission(Perms.PRIVILEGED)
        await ctx.reply(self.commands.message('PRIV_ONLY', 'set'))

    async def djs_only(self, ctx: Context):
        self.settings.set_permission(Perms.DJS)
        await ctx.reply(self.commands.message('DJS_ONLY', 'set'))

    async def all_perms(self, ctx: Context):
        self.settings.set_permission(Perms.ALL)
        await ctx.reply(self.commands.message('ALL', 'set'))
