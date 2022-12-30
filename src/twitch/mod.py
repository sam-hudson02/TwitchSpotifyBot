from twitchio.ext import commands
from utils.errors import *
import threading as th

class ModCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log = bot.log
        self.db = bot.db
        self.ac = bot.ac
        self.settings = bot.settings
        self.units = bot.units
        self.channel_name = bot.channel_name

    async def cog_check(self, ctx: commands.Context) -> bool:
        if not self.db.is_user_privileged(ctx.author.name.lower()):
            raise NotAuthorized('mod')
        return True

    @commands.command(name='skip')
    async def skip(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        self.check_user(user)

        if not self.settings.get_active():
            raise NotActive
        if not self.bot.is_live:
            resp = f'Song request are currently turned off. ({self.channel_name} not live)'
            await ctx.reply(resp)
            self.log.resp(resp)
            return False

        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))
        self.log.req(user, request, str(ctx.command.name))
        if self.db.is_user_privileged(user):
            await self.ac.play_next(skipped=True)
            resp = f'Skipping current track!'
            await ctx.reply(resp)
            self.log.resp(resp)
        else:
            raise NotAuthorized('mod')

    @commands.command(name='sp-ban')
    async def ban_command(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        self.check_user(user)
        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))

        self.log.req(user, request, ctx.command.name)

        target = self.target_finder(request)

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
        self.check_user(user)

        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))

        self.log.req(user, request, ctx.command.name)

        target = self.target_finder(request)

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
        self.check_user(user)

        com = str(ctx.prefix + ctx.command.name + ' ')
        request = ctx.message.content
        request = request.replace(com, '')

        self.log.req(user, request, ctx.command.name)

        target = self.target_finder(request)

        time_ = request.replace(f'@{target} ', '')
        time_ = time_.strip(' ')

        try:
            time_returned = self.time_finder(time_)
            if self.ban(user, target):
                resp = f'@{target} has been timed out for {time_returned["time"]} ' \
                       f'{self.units_full[time_returned["unit"]]}.'
                await ctx.reply(resp)
                self.log.resp(resp)
                time_secs = time_returned['time'] * \
                    self.units[time_returned['unit']]
                try:
                    th.Timer(time_secs, self.unban, [user, target])
                except UserAlreadyRole:
                    self.log.info(
                        f'Timeout ended for {target}, user already unbanned.')
        except ValueError:
            raise TimeNotFound