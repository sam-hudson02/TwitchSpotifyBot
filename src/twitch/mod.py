from prisma.models import User
from utils.errors import NotAuthorized, NotActive
from utils import target_finder, Settings, DB, Perms
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

    async def load(self):
        self.bot.router.add_route('skip', self.skip, self)
        self.bot.router.add_route('ban', self.ban_command, self)
        self.bot.router.add_route('unban', self.unban_command, self)
        self.bot.router.add_route('followers-only', self.followers_only, self)
        self.bot.router.add_route('subs-only', self.subs_only, self)
        self.bot.router.add_route('priv-only', self.privileged_only, self)
        self.bot.router.add_route('all', self.all_perms, self)

    async def before_invoke(self, ctx: Context) -> bool:
        if not ctx.user.mod or not ctx.user.admin:
            raise NotAuthorized('mod')
        return True

    async def skip(self, ctx: Context):
        if not self.settings.active or self.ac.context.paused:
            raise NotActive
        if not self.ac.context.live:
            await ctx.reply(f'Song request are currently turned off.'
                            f' ({self.channel} not live)')
            return

        await self.ac.play_next(skipped=True)
        await ctx.reply('Skipping current track!')

    async def ban_command(self, ctx: Context):
        target_username = target_finder(ctx.content)
        target = await self.db.get_user(target_username)

        if await self.ban(ctx.user, target):
            await ctx.reply(f'@{target} has been banned!')

    async def ban(self, user: User, target: User):
        # if the user is an admin ban the target even if they're a mod
        if user.admin:
            if target.admin:
                return False
            await self.db.ban_user(target.username)
            return True

        # if the user is a mod and the target isn't
        # a mod or admin then ban the target
        elif user.mod and not (target.mod or target.admin):
            await self.db.ban_user(target.username)
            return True

        else:
            raise NotAuthorized('mod/admin')

    async def unban_command(self, ctx: Context):
        target_username = target_finder(ctx.content)
        await self.db.unban_user(target_username)
        await ctx.reply(f'@{target_username} has been unbanned!')

    async def followers_only(self, ctx: Context):
        self.settings.set_permission(Perms.FOLLOWERS)
        await ctx.reply('Song requests are now open to followers '
                        'only.')

    async def subs_only(self, ctx: Context):
        self.settings.set_permission(Perms.SUBS)
        await ctx.reply('Song requests are now open to subscribers '
                        'only.')

    async def privileged_only(self, ctx: Context):
        self.settings.set_permission(Perms.PRIVILEGED)
        await ctx.reply('Song requests are now open to privileged '
                        'users only.')

    async def all_perms(self, ctx: Context):
        self.settings.set_permission(Perms.ALL)
        await ctx.reply('Song requests are now open to everyone.')
