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
        self.commands = bot.commands

    async def before_invoke(self, ctx: Context) -> bool:
        if not ctx.user.mod:
            raise NotAuthorized(clearance_required='mod')
        return True

    async def load(self):
        self.register('SET_VETO', self.set_veto_pass)
        self.register('ADD_MOD', self.add_mod)
        self.register('REMOVE_MOD', self.remove_mod)
        self.register('SR_ON', self.sp_on)
        self.register('SR_OFF', self.sp_off)
        self.register('LEADERBOARD_RESET', self.leaderboard_reset)
        self.register('CLEAR', self.clear_queue)
        self.register('DEV_ON', self.dev_on)
        self.register('DEV_OFF', self.dev_off)

    async def set_veto_pass(self, ctx: Context):
        try:
            new_veto_pass = int(ctx.content)
            if new_veto_pass < 2:
                await ctx.reply(self.commands.message('SET_VETO', 'too_low'))
            else:
                self.settings.set_veto_pass(int(ctx.content))
                await ctx.reply(self.commands.message('SET_VETO', 'set',
                                                      veto_pass=new_veto_pass))
        except ValueError:
            await ctx.reply(self.commands.message('SET_VETO', 'not_a_number'))

    def set_active(self, active: bool):
        self.settings.set_active(active)
        self.ac.context.active = active

    def set_live(self, live: bool):
        self.ac.context.live = live

    async def add_mod(self, ctx: Context):
        target = target_finder(ctx.content)

        await self.db.mod_user(target)
        await ctx.reply(self.commands.message('ADD_MOD', 'modded',
                                              target=target))

    async def remove_mod(self, ctx: Context):
        target = target_finder(ctx.content)

        await self.db.unmod_user(target)
        await ctx.reply(self.commands.message('REMOVE_MOD', 'unmodded',
                                              target=target))

    async def sp_on(self, ctx: Context):
        if not self.settings.active:
            self.set_active(True)
            await ctx.reply(self.commands.message('SR_ON', 'on'))
        elif self.ac.context.live:
            await ctx.reply(self.commands.message('SR_ON', 'already_on_not_live',
                                                  channel=self.channel))
        else:
            await ctx.reply(self.commands.message('SR_ON', 'already_on'))

    async def sp_off(self, ctx: Context):
        if self.settings.active:
            self.set_active(False)
            await ctx.reply(self.commands.message('SR_OFF', 'off'))
        else:
            await ctx.reply(self.commands.message('SR_OFF', 'already_off'))

    async def leaderboard_reset(self, ctx: Context):
        await self.db.reset_all_user_stats()
        await ctx.reply(self.commands.message('LEADERBOARD_RESET', 'reset'))

    async def clear_queue(self, ctx: Context):
        await self.db.clear_queue()
        await ctx.reply(self.commands.message('CLEAR', 'cleared'))

    async def dev_on(self, ctx: Context):
        self.settings.set_dev_mode(True)
        await ctx.reply(self.commands.message('DEV_ON', 'on'))

    async def dev_off(self, ctx: Context):
        self.settings.set_dev_mode(False)
        await ctx.reply(self.commands.message('DEV_OFF', 'off'))
