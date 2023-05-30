from utils.errors import NotAuthorized
from utils import target_finder, Settings, DB
from twitch.cog import Cog
from twitch.router import Context
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from twitch.bot import Bot as TwitchBot


class AdminCog(Cog):
    def __init__(self, bot: "TwitchBot"):
        self.bot = bot
        self.db: DB = bot.db
        self.ac = bot.ac
        self.settings: Settings = bot.settings
        self.channel = bot.channel

    async def before_invoke(self, ctx: Context) -> bool:
        if not ctx.user.mod:
            raise NotAuthorized(clearance_required='mod')
        return True

    async def load(self):
        self.bot.router.add_route('set-veto', self.set_veto_pass, self)
        self.bot.router.add_route('sr-mod', self.add_mod, self)
        self.bot.router.add_route('sr-unmod', self.remove_mod, self)
        self.bot.router.add_route('sr-on', self.sp_on, self)
        self.bot.router.add_route('sr-off', self.sp_off, self)
        self.bot.router.add_route('sr-reset', self.leaderboard_reset, self)
        self.bot.router.add_route('clear', self.clear_queue, self)
        self.bot.router.add_route('dev-on', self.dev_on, self)
        self.bot.router.add_route('dev-off', self.dev_off, self)

    async def set_veto_pass(self, ctx: Context):
        try:
            new_veto_pass = int(ctx.content)
            if new_veto_pass < 2:
                await ctx.reply('Veto pass must be at least 2')
            else:
                self.settings.set_veto_pass(int(ctx.content))
                await ctx.reply('Veto pass has been set to '
                                f'{new_veto_pass}')
        except ValueError:
            await ctx.reply('Could not find a number in your '
                            'command')

    def set_active(self, active: bool):
        self.settings.set_active(active)
        self.ac.context.active = active

    def set_live(self, live: bool):
        self.ac.context.live = live

    async def add_mod(self, ctx: Context):
        target = target_finder(ctx.content)

        await self.db.mod_user(target)
        await ctx.reply(f'@{target} is now a mod! Type !sp-help '
                        'to see all the available commands!')

    async def remove_mod(self, ctx: Context):
        target = target_finder(ctx.content)

        await self.db.unmod_user(target)
        await ctx.reply(f'@{target} is no longer a mod.')

    async def sp_on(self, ctx: Context):
        if not self.settings.active:
            self.set_active(True)
            await ctx.reply('Song request have been turned on!')
        elif self.ac.context.live:
            await ctx.reply("Song request are already turned on but "
                            f"won't be taken till {self.channel} is "
                            "live.")
        else:
            await ctx.reply('Song request are already turned on.')

    async def sp_off(self, ctx: Context):
        if self.settings.active:
            self.set_active(False)
            await ctx.reply('Song request have been turned off!')
        else:
            await ctx.reply('Song request are already turned off.')

    async def leaderboard_reset(self, ctx: Context):
        await self.db.reset_all_user_stats()
        await ctx.reply('Leaderboard has been reset!')

    async def clear_queue(self, ctx: Context):
        await self.db.clear_queue()
        await ctx.reply('Queue has been cleared!')

    async def dev_on(self, ctx: Context):
        self.settings.set_dev_mode(True)
        await ctx.reply('Dev mode has been turned on!')

    async def dev_off(self, ctx: Context):
        self.settings.set_dev_mode(False)
        await ctx.reply('Dev mode has been turned off!')
