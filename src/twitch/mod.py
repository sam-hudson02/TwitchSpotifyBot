from twitchio.ext import commands
from utils.errors import *
from utils import Timer, time_finder, target_finder

class ModCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log = bot.log
        self.db = bot.db
        self.ac = bot.ac
        self.settings = bot.settings
        self.units = bot.units
        self.channel_name = bot.channel_name
        self.units_full = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}

    async def cog_check(self, ctx: commands.Context) -> bool:
        if not self.db.is_user_privileged(ctx.author.name.lower()):
            raise NotAuthorized('mod')
        return True

    @commands.command(name='skip')
    async def skip(self, ctx: commands.Context):
        if not self.settings.active:
            raise NotActive
        if not self.bot.is_live:
            resp = f'Song request are currently turned off. ({self.channel_name} not live)'
            await ctx.reply(resp)
            self.log.resp(resp)
            return False

        await self.ac.play_next(skipped=True)
        resp = f'Skipping current track!'
        await ctx.reply(resp)
        self.log.resp(resp)

    @commands.command(name='sp-ban')
    async def ban_command(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))

        target = target_finder(self.db, request)

        if self.ban(user, target):
            resp = f'@{target} has been banned!'
            await ctx.reply(resp)
            self.log.resp(resp)

    def ban(self, user, target):
        # if the user is an admin ban the target even if they're a mod
        if self.db.is_user_admin(user):
            self.db.ban_user(target)
            return True

        # if the user is a mod and the target isn't a mod or admin then ban the target
        elif self.db.is_user_mod(user) and not self.db.is_user_privileged(target):
            self.db.ban_user(target)
            return True

        else:
            raise NotAuthorized('mod/admin')

    @commands.command(name='sp-unban')
    async def unban_command(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))

        target = target_finder(self.db, request)

        if self.unban(user, target):
            resp = f'@{target} has been unbanned!'
            await ctx.reply(resp)
            self.log.resp(resp)

    def unban(self, user, target):
        # if user is a mod or admin and target is banned then unban them
        if self.db.is_user_privileged(user):
            self.db.unban_user(target)
            return True
        else:
            raise NotAuthorized('mod/admin')

    @commands.command(name='sp-timeout')
    async def timeout(self, ctx: commands.Context):
        user = ctx.author.name.lower()

        com = str(ctx.prefix + ctx.command.name + ' ')
        request = ctx.message.content
        request = request.replace(com, '')

        target = target_finder(self.db, request)

        time_ = request.replace(f'@{target} ', '')
        time_ = time_.strip(' ')

        try:
            time_returned = time_finder(time_)
            if self.ban(user, target):
                resp = f'@{target} has been timed out for {time_returned["time"]} ' \
                       f'{self.units_full[time_returned["unit"]]}.'
                await ctx.reply(resp)
                self.log.resp(resp)
                time_ms = (time_returned['time'] * \
                    self.units[time_returned['unit']]) * 1000
                try:
                    Timer(time_ms, self.unban, [user, target])
                except UserAlreadyRole:
                    self.log.info(
                        f'Timeout ended for {target}, user already unbanned.')
        except ValueError:
            raise TimeNotFound