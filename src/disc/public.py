import functools
import datetime
import discord
from discord.ext import commands
from table2ascii import table2ascii as t2a, PresetStyle
from utils.errors import UserNotFound, NotActive, TrackNotFound
from utils import Log, Settings, DB


class PublicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db: DB = bot.db
        self.log: Log = bot.log
        self.settings: Settings = bot.settings
        self.ac = bot.ac
    
    async def cog_app_command_error(self, ctx, error):
        error = getattr(error, 'original', error)
        if isinstance(error, UserNotFound):
            resp = f'User "{error.user}" not found in database.'
        elif isinstance(error, NotActive):
            resp = 'Bot is not active.'
        elif isinstance(error, TrackNotFound):
            resp = 'Track not found.'
        else:
            resp = f'An unknown error occurred.'
        self.log.resp(resp)
        self.log.error(error)
        await ctx.response.send_message(content=resp, ephemeral=True)
    
    async def cog_before_invoke(self, ctx: discord.Interaction) -> None:
        user = ctx.user.name + '#' + ctx.user.discriminator
        if ctx.message is None:
            request = ''
        else:
            request = ctx.message.content
        command = ctx.command.name
        self.log.req(user, request, command)
    
    def check():
        def wrapper(func):
            @functools.wraps(func)
            async def wrapped(self, *args, **kwargs):
                await self.cog_before_invoke(args[0])
                return await func(self, *args, **kwargs)
            return wrapped
        return wrapper
        
    @discord.app_commands.command(name='stats', description='Gets song request stats of given twitch user.')
    @discord.app_commands.describe(twitch_username='Enter twitch username (not case sensitive)')
    @check()
    async def get_stats(self, interaction: discord.Interaction, twitch_username: str):
        twitch_username = twitch_username.lower()

        stats = self.db.get_user_stats(twitch_username)
        if stats is None:
            raise UserNotFound(twitch_username)

        position = stats['pos']
        rates = stats['rates']
        requests = stats['requests']
        rates_given = stats['rates given']
        if rates != 0 and requests != 0:
            perc = str(round(((rates / requests) * 100), 2)) + '%'
        else:
            perc = 'na'
        header = ['Position', 'Rates', 'Request',
                    'Rate Percentage', 'Rates Given']
        body = [[str(position), str(rates), str(
            requests), perc, str(rates_given)]]
        await interaction.response.send_message(content=f"```\n"
                                                f"{t2a(header=header, body=body, style=PresetStyle.thin_rounded)}"
                                                f"\n```", ephemeral=True)
    
    @discord.app_commands.command(name='queue', description='add a track to queue')
    @discord.app_commands.describe(request='enter request')
    @check()
    async def queue(self, interaction: discord.Interaction, request: str):
        if not self.ac.context.live or not self.settings.active:
            raise NotActive

        track, artist = self.ac.add_to_queue(request, interaction.user)

        if not track:
            raise TrackNotFound
        
        resp = f'Added {track} by {artist} to the queue!'

        await interaction.response.send_message(content=resp, ephemeral=True)
        self.log.resp(resp)
        return None

    @discord.app_commands.command(name='ping', description='pong')
    @check()
    async def pong(self, interaction: discord.Interaction):
        embed = self.get_pong_embed(interaction)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        self.log.resp('pong')

    def get_pong_embed(self, ctx: discord.Integration):
        embed = discord.Embed(title='🏓 Pong!')
        
        latency = round(self.bot.latency, 2)
        embed.add_field(name='Latency', value=f'{latency} seconds', inline=False)

        cogs = self.get_running_cogs()
        embed.add_field(name='Cogs Running', value=cogs, inline=False)

        routines = self.get_running_routines()
        embed.add_field(name='Routines Running', value=routines, inline=False)
        
        status = self.get_status()
        embed.add_field(name='Status', value=status, inline=False)
        return embed

    def get_running_cogs(self) -> str:
        cogs_running = [cog for cog in self.bot.cogs.keys()]
        cogs = []
        all_cogs = self.bot.online_cogs + self.bot.offline_cogs
        for cog in all_cogs:
            if cog.__cog_name__ in cogs_running:
                cogs.append(f'{cog.__cog_name__}: 🟢 Running')
            else:
                cogs.append(f'{cog.__cog_name__}: 🔴 Not Running')
        return '\n'.join(cogs)
    
    def get_running_routines(self) -> str:
        routines = {'Check Live': False, 'Update Playing': False, 'Update Queue': False, 'Update Leaderboard': False}
        routines['Check Live'] = self.bot.check_live.is_running()
        routines_str_list = []
        if self.bot.get_cog('AutoUpdate') is not None:
            routines['Update Playing'] = self.bot.get_cog('AutoUpdate').get_context.is_running()
            routines['Update Queue'] = self.bot.get_cog('AutoUpdate').get_queue.is_running()
            routines['Update Leaderboard'] = self.bot.get_cog('AutoUpdate').get_leaderboard.is_running()
        
        for routine in routines.keys():
            if routines[routine]:
                routines_str_list.append(f'{routine}: 🟢 Running')
            else:
                routines_str_list.append(f'{routine}: 🔴 Not Running')
        return '\n'.join(routines_str_list)

    def get_status(self) -> str:
        status_live = self.ac.context.live
        status_active = self.settings.active
        status_str_list = []
        if status_live:
            status_str_list.append('Live Status: 🟢 Online')
        else:
            status_str_list.append('Live Status: 🔴 Offline')
        if status_active:
            status_str_list.append(f'SR Status: 🟢 Active ({self.settings.permission.value})')
        else:
            status_str_list.append('SR Status: 🔴 Inactive')
        return '\n'.join(status_str_list)
