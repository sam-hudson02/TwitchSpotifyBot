from twitchio.ext import commands
from utils.errors import NotAuthorized
from utils import target_finder, Settings, DB, Log, get_message
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from twitch_bot import TwitchBot


class AdminCog(commands.Cog):
    def __init__(self, bot: "TwitchBot"):
        self.bot = bot
        self.log: Log = bot.log
        self.db: DB = bot.db
        self.ac = bot.ac
        self.settings: Settings = bot.settings
        self.channel_name = bot.channel_name

    async def cog_check(self, ctx: commands.Context) -> bool:
        if ctx.author.name is None:
            raise NotAuthorized(clearance_required='mod')
        username = ctx.author.name.lower()
        user = await self.db.get_user(username)
        if not user.mod:
            raise NotAuthorized(clearance_required='mod')
        return True

    @commands.command(name='sp-set-veto-pass')
    async def set_veto_pass(self, ctx: commands.Context):
        request = get_message(ctx)
        try:
            new_veto_pass = int(request)
            if new_veto_pass < 2:
                await self.bot.reply(ctx, 'Veto pass must be at least 2')
            else:
                self.settings.set_veto_pass(int(request))
                await self.bot.reply(ctx,
                                     'Veto pass has been set to '
                                     f'{new_veto_pass}')
        except ValueError:
            await self.bot.reply(ctx, 'Could not find a number in your '
                                 'command')

    def set_active(self, active: bool):
        self.settings.set_active(active)
        self.ac.context.active = active

    def set_live(self, live: bool):
        self.bot.is_live = live
        self.ac.context.live = live

    @commands.command(name='sp-mod')
    async def add_mod(self, ctx: commands.Context):
        request = get_message(ctx)
        target = target_finder(request)

        await self.db.mod_user(target)
        await self.bot.reply(ctx, f'@{target} is now a mod! Type !sp-help '
                             'to see all the available commands!')

    @commands.command(name='sp-unmod')
    async def remove_mod(self, ctx: commands.Context):
        request = get_message(ctx)
        target = target_finder(request)

        await self.db.unmod_user(target)
        await self.bot.reply(ctx, f'@{target} is no longer a mod.')

    @commands.command(name='sp-on')
    async def sp_on(self, ctx: commands.Context):
        if not self.settings.active:
            self.set_active(True)
            resp = 'Song request have been turned on!'
            await ctx.reply(resp)
            self.log.resp(resp)
        elif self.bot.is_live:
            await self.bot.reply(ctx, "Song request are already turned on but "
                                 f"won't be taken till {self.channel_name} is "
                                 "live.")
        else:
            await self.bot.reply(ctx, 'Song request are already turned on.')

    @commands.command(name='sp-off')
    async def sp_off(self, ctx: commands.Context):
        if self.settings.active:
            self.set_active(False)
            await self.bot.reply(ctx, 'Song request have been turned off!')
        else:
            await self.bot.reply(ctx, 'Song request are already turned off.')

    @commands.command(name='sp-lb-reset')
    async def leaderboard_reset(self, ctx: commands.Context):
        await self.db.reset_all_user_stats()
        await self.bot.reply(ctx, 'Leaderboard has been reset!')

    @commands.command(name='sp-clear-queue')
    async def clear_queue(self, ctx: commands.Context):
        await self.db.clear_queue()
        await self.bot.reply(ctx, 'Queue has been cleared!')

    @commands.command(name='sp-dev-on')
    async def dev_on(self, ctx: commands.Context):
        self.settings.set_dev_mode(True)
        await self.bot.reply(ctx, 'Dev mode has been turned on!')

    @commands.command(name='sp-dev-off')
    async def dev_off(self, ctx: commands.Context):
        self.settings.set_dev_mode(False)
        await self.bot.reply(ctx, 'Dev mode has been turned off!')
