from prisma.models import User
from twitchio.ext import commands
from utils.errors import NotAuthorized, NotActive
from utils import Timer, time_finder, get_message, target_finder, Settings, DB, Log, Perms, get_username


class ModCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log: Log = bot.log
        self.db: DB = bot.db
        self.ac = bot.ac
        self.settings: Settings = bot.settings
        self.units = bot.units
        self.channel_name = bot.channel_name
        self.units_full = {"s": "seconds",
                           "m": "minutes", "h": "hours", "d": "days"}

    async def cog_check(self, ctx: commands.Context) -> bool:
        username = get_username(ctx)
        user = await self.db.get_user(username)
        if not user.mod or not user.admin:
            raise NotAuthorized('mod')
        return True

    @commands.command(name='skip')
    async def skip(self, ctx: commands.Context):
        if not self.settings.active:
            raise NotActive
        if not self.bot.is_live:
            await self.bot.reply(ctx, f'Song request are currently turned off.'
                                 f' ({self.channel_name} not live)')
            return False

        await self.ac.play_next(skipped=True)
        await self.bot.reply(ctx, 'Skipping current track!')

    @commands.command(name='sp-ban')
    async def ban_command(self, ctx: commands.Context):
        request = get_message(ctx)
        username = get_username(ctx)
        target_username = target_finder(request)

        user = await self.db.get_user(username)
        target = await self.db.get_user(target_username)

        if await self.ban(user, target):
            await self.bot.reply(ctx, f'@{target} has been banned!')

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

    @commands.command(name='sp-unban')
    async def unban_command(self, ctx: commands.Context):
        request = get_message(ctx)
        target_username = target_finder(request)

        await self.db.unban_user(target_username)
        await self.bot.reply(f'@{target_username} has been unbanned!')

    @commands.command(name='sp-followers')
    async def followers_only(self, ctx: commands.Context):
        self.settings.set_permission(Perms.FOLLOWERS)
        await self.bot.reply(ctx, 'Song requests are now open to followers '
                             'only.')

    @commands.command(name='sp-subs')
    async def subs_only(self, ctx: commands.Context):
        self.settings.set_permission(Perms.SUBS)
        await self.bot.reply(ctx, 'Song requests are now open to subscribers '
                             'only.')

    @commands.command(name='sp-priv')
    async def privileged_only(self, ctx: commands.Context):
        self.settings.set_permission(Perms.PRIVILEGED)
        await self.bot.reply(ctx, 'Song requests are now open to privileged '
                             'users only.')

    @commands.command(name='sp-all')
    async def all_perms(self, ctx: commands.Context):
        self.settings.set_permission(Perms.ALL)
        await self.bot.reply(ctx, 'Song requests are now open to everyone.')
