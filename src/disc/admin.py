import discord
import functools
from discord.ext import commands
from utils.errors import NotAuthorized
from utils import Log, Settings
from AudioController.audio_controller import AudioController
import requests

discord.app_commands.tree


class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ac: AudioController = bot.ac
        self.settings: Settings = bot.settings
        self.log: Log = bot.log
        self.db = bot.db

    async def cog_before_invoke(self, ctx: discord.Integration) -> None:
        user = ctx.user.name + '#' + ctx.user.discriminator
        if ctx.message is None:
            request = ''
        else:
            request = ctx.message.content
        command = ctx.command.name
        self.log.req(user, request, command)
        if not getattr(ctx.permissions, 'administrator', False):
            raise NotAuthorized('administrator')

    def check():
        def wrapper(func):
            @functools.wraps(func)
            async def wrapped(self, *args, **kwargs):
                await self.cog_before_invoke(args[0])
                return await func(self, *args, **kwargs)
            return wrapped
        return wrapper

    async def cog_app_command_error(self, ctx, error):
        error = getattr(error, 'original', error)
        if isinstance(error, NotAuthorized):
            resp = 'Sorry, you need to be a server admin to use this command.'
        else:
            resp = 'An unknown error occurred'
        await ctx.response.send_message(resp)
        self.log.resp(resp)
        self.log.error(error)

    @discord.app_commands.command(name='reset_leaderboard', description='Reset the leaderboard')
    @check()
    async def reset_leaderboard(self, interaction: discord.Interaction):
        self.db.reset_all_user_stats()
        resp = "The leaderboard has been reset!"
        await interaction.response.send_message(content=resp, ephemeral=True)
        self.log.resp(resp)

    @discord.app_commands.command(name='restart', description='Restart the bot')
    async def restart(self, interaction: discord.Interaction):
        resp = "Restarting..."
        await interaction.response.send_message(content=resp, ephemeral=True)
        self.log.resp(resp)
        requests.get('http://localhost:5000/restart-bot')
