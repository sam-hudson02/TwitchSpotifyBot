import discord
from discord.ext import commands
from utils.errors import NotAuthorized, DBError
from utils import Log, Settings
from AudioController.audio_controller import AudioController
import functools


class ModCog(commands.Cog):
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
        roles = [role.name for role in ctx.user.roles]
        if 'DJ' not in roles:
            raise NotAuthorized('DJ')

    def check():
        def wrapper(func):
            @functools.wraps(func)
            async def wrapped(self, *args, **kwargs):
                await self.cog_before_invoke(args[0])
                return await func(self, *args, **kwargs)
            return wrapped
        return wrapper

    async def cog_app_command_error(self, ctx, error) -> None:
        error = getattr(error, 'original', error)
        if isinstance(error, NotAuthorized):
            resp = 'Sorry, you need the role "DJ" to use this command.'
        elif isinstance(error, DBError):
            resp = 'a database error occurred while processing your request'
        else:
            resp = 'An unknown error occurred while processing your request'
        await ctx.response.send_message(content=resp, ephemeral=True)
        self.log.resp(resp)
        self.log.error(error)

    @discord.app_commands.command(name='skip', description='Skip the current song')
    @check()
    async def skip(self, ctx):
        if self.settings.active and self.ac.context.live:
            await self.ac.play_next(skipped=True)
            resp = 'Skipping current track!'
        else:
            resp = 'Nothing to skip!'

        await ctx.response.send_message(content=resp, ephemeral=True)
        self.log.resp(resp)

    @discord.app_commands.command(name='clear-queue', description='Clear request queue display (admin only)')
    @check()
    async def clear_queue(self, interaction: discord.Interaction):
        self.db.clear_queue()
        resp = 'Queue has been cleared!'
        await interaction.response.send_message(content=resp, ephemeral=True)
        self.log.resp(resp)

    @discord.app_commands.command(name='bump', description='Moves a track to the top of the queue ')
    @discord.app_commands.describe(request_id='end the request id of the track')
    @check()
    async def bump(self, interaction: discord.Interaction, request_id: int):
        if self.db.move_request_pos(request_id):
            resp = 'Track moved to top of the queue'
        else:
            resp = 'Could not find track in queue'
        await interaction.response.send_message(content=resp, ephemeral=True)
        self.log.resp(resp)

    @discord.app_commands.command(name='remove-request', description='Remove song request from queue display by track name. (admin only)')
    @discord.app_commands.describe(req_id='enter request id')
    @check()
    async def remove_request(self, interaction: discord.Interaction, req_id: int):
        track, artist = self.db.remove_from_queue_by_id(req_id)
        if track is not None:
            await interaction.response.send_message(content=f'removed "{track} by {artist}" from queue', ephemeral=True)
        else:
            await interaction.response.send_message(content=f'Could not find id: "{req_id}" in queue', ephemeral=True)
