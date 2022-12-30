import discord
import sys
import traceback
import time
from utils.logger import Log
from spotify_api import Spotify
from utils.db_handler import DB
from discord.ext import tasks, commands
from table2ascii import table2ascii as t2a, PresetStyle
from audio_controller import AudioController
from utils.errors import *


class DiscordBot(commands.Bot):
    def __init__(self, leaderboard_channel_id, queue_channel_id, twitch_channel, log: Log,
                 spot: Spotify, db: DB, ac: AudioController):
        super().__init__('/', intents=discord.Intents.default())
        self.ac = ac
        self.log = log
        self.spot = spot
        self.db = db
        self.leaderboard_channel_id = int(leaderboard_channel_id)
        self.queue_channel_id = int(queue_channel_id)
        self.twitch_channel = twitch_channel

    async def on_ready(self) -> None:
        self.log.info('Discord bot listening.')
        await self.add_cog(Commands(self.twitch_channel, self, self.db, self.spot, self.ac))
        leaderboard_channel = self.get_channel(self.leaderboard_channel_id)
        queue_channel = self.get_channel(self.queue_channel_id)
        await self.add_cog(AutoUpdate(leaderboard_channel, queue_channel, self.twitch_channel,
                                      self, self.db, self.ac))
        synced = await self.tree.sync()
        self.log.info(f'synced {len(synced)} commands')
    
    async def on_disconnect(self):
        self.log.info('Bot disconnected.')
        while self.is_closed():
            time.sleep(5)
            self.log.info('Bot attempting reconnecting.')
        if not self.is_closed():
            self.log.info('Bot reconnected.')
            cog = self.get_cog('AutoUpdate')
            print(cog)
            leaderboard_channel = self.get_channel(self.leaderboard_channel_id)
            queue_channel = self.get_channel(self.queue_channel_id)
            if cog is not None:
                await self.remove_cog('AutoUpdate')
                await self.add_cog(AutoUpdate(leaderboard_channel, queue_channel, self.twitch_channel,
                                            self, self.db, self.ac))
            else:
                await self.bot.add_cog(AutoUpdate(leaderboard_channel, leaderboard_channel,
                                                self.twitch_channel, self.bot, self.db, self.ac))

class AutoUpdate(commands.Cog):
    def __init__(self, leaderboard_channel, queue_channel, twitch_channel, bot: DiscordBot, db: DB,
                 ac: AudioController):
        self.ac = ac
        self.db = db
        self.bot = bot
        self.log = self.bot.log
        self.spot = self.bot.spot
        self.leaderboard_channel = leaderboard_channel
        self.queue_channel = queue_channel
        self.twitch_channel = twitch_channel
        self.leaderboard = discord.Embed(
            title=f'{twitch_channel} Song Request Leaderboard')
        self.queue = []
        self.leaderboard_message_obj = None
        self.queue_message_obj = None
        self.playing_message_obj = None
        self.context = None
        self.leaderboard = None
        self.get_leaderboard.start()
        self.get_queue.start()
        self.get_context.start()
    
    def embed_leaderboard(self):
        sorted_position, sorted_users, sorted_rates = self.db.get_leaderboard()
        embed = discord.Embed(
                title=f'{self.twitch_channel} Song Request Leaderboard')
        if len(sorted_users) > 0:
            embed.add_field(name='Position',
                            value=sorted_position, inline=True)
            embed.add_field(name='User', value=sorted_users, inline=True)
            embed.add_field(name='Rates', value=sorted_rates, inline=True)
        else:
            embed.add_field(name='Leaderboard is currently empty!',
                            value='No has received any rates yet!')
        return embed

    def embed_queue(self):
        q = self.queue
        if len(q) > 0:
            i = 1
            body = []
            header = ['Position', 'Track', 'Artist/s', 'Requester', 'id']
            for req in q[:5]:
                req_id = req[0]
                pos = req[1]
                track = req[2]
                artist = req[3]
                user = req[4]
                position = str(pos)
                body.append([position, track, artist, user, req_id])
                i += 1

            queue_content = f"{self.twitch_channel} Song Request Queue: \n" \
                            f"```\n{t2a(header=header, body=body, style=PresetStyle.thin_rounded)}\n```"
        else:
            queue_content = f"{self.twitch_channel} Song Request Queue: \n" \
                            f"```\nQueue is Currently Empty!\n```"

        if len(queue_content) < 2000:
            return queue_content
        else:
            return 'Problem with queue :/'

    async def cog_unload(self) -> None:
        self.get_leaderboard.cancel()
        self.get_context.cancel()
        self.get_queue.cancel()

    async def get_message_obj_queue(self):
        self.log.info('Getting queue message object')
        messages = [message async for message in self.queue_channel.history()]
        if len(messages) == 1:
            if messages[0].author == self.bot.user:
                self.queue_message_obj = messages[0]
                return None
            else:
                await self.queue_channel.purge()
                self.queue_message_obj = await self.queue_channel.send(f'Empty')
        elif len(messages) > 1:
            await self.queue_channel.purge()
            self.queue_message_obj = await self.queue_channel.send(f'Empty')
        else:
            self.queue_message_obj = await self.queue_channel.send(f'Empty')

    async def get_message_obj_leaderboard(self):
        self.log.info('Getting leaderboard message object')
        messages = [message async for message in self.leaderboard_channel.history()]
        if len(messages) == 1:
            if messages[0].author == self.bot.user:
                self.leaderboard_message_obj = messages[0]
                return None
        elif len(messages) > 1:
            await self.leaderboard_channel.purge()
            self.leaderboard_message_obj = await self.leaderboard_channel.send(f'Empty')

    async def update_playing(self):
        if self.queue_message_obj is None:
            return None

        context = self.context
        queue = self.embed_queue()

        embed = None

        if context is None:
            return

        if not context['paused'] and self.ac.context.active and self.ac.context.live:
            track_info = f'{context["track"]} - {context["artist"]}'
            image = context['album_art']
            embed = discord.Embed(
                title=f'Currently playing:', colour=discord.Colour.purple())
            embed.set_image(url=image)
            embed.add_field(name=track_info,
                            value='----------------------------------------------------', inline=False)
            if context['playing_queue']:
                embed.set_footer(text=f'requested by {context["requester"]}')

        await self.queue_message_obj.edit(content=queue, embed=embed, view=None)

    @tasks.loop(seconds=2)
    async def get_queue(self):
        if self.queue_message_obj is None:
            return None

        new_queue = self.db.get_queue()

        if new_queue != self.queue:
            self.queue = new_queue
            self.log.info('updating queue')
            await self.update_playing()

    @tasks.loop(seconds=2)
    async def get_context(self):
        if self.queue_message_obj is None:
            return None
        ctx_loaded = self.ac.context.get_context()
        new_ctx = {"paused": ctx_loaded["paused"],
                    "track": ctx_loaded["track"],
                    "artist": ctx_loaded["artist"],
                    "album_art": ctx_loaded["album_art"],
                    "requester": ctx_loaded["requester"],
                    "playing_queue": ctx_loaded["playing_queue"],
                    "live": ctx_loaded["live"],
                    "active": ctx_loaded["active"]
                    }
        if new_ctx != self.context:
            self.context = new_ctx
            self.log.info('updating context')
            await self.update_playing()

    @tasks.loop(seconds=2)
    async def get_leaderboard(self):
        if self.leaderboard_message_obj is None:
            return None

        new_leaderboard = self.db.get_leaderboard()
        if new_leaderboard != self.leaderboard:
            self.leaderboard = new_leaderboard
            self.log.info('updating leaderboard')
            await self.update_leaderboard()

    @get_leaderboard.error
    @get_queue.error
    @get_context.error
    async def task_error_handler(self, error):
        if isinstance(error, discord.errors.DiscordServerError):
            self.log.error(f'discord server error: {error}')
        elif isinstance(error, discord.errors.NotFound):
            self.log.error(f'Message object not found, restarting cog')
            await self.restart_cog()
        else:
            self.log.error(f'Unexpected error: {error}')
            raise error
            

    async def update_leaderboard(self):
        if self.leaderboard_message_obj is None:
            return None
        try:
            leaderboard = self.embed_leaderboard()
            await self.bot.wait_until_ready()
            try:
                await self.leaderboard_message_obj.edit(content='', embed=leaderboard)
            except discord.HTTPException as http_er:
                # if the message is over discord's character limit,
                # the leaderboard will be cut by one user at a time until it's less than limit.
                self.log.error(f'update leaderboard http er: {http_er}')

        except discord.errors.DiscordServerError as disc_er:
            self.log.error(f'updates leader board er: {disc_er}')
            return True

    @get_leaderboard.before_loop
    async def before_update_leaderboard(self):
        self.log.info('Starting AutoUpdate..')
        await self.bot.wait_until_ready()
        await self.get_message_obj_leaderboard()
        await self.get_message_obj_queue()

    async def before_update_queue(self):
        await self.bot.wait_until_ready()

    @discord.app_commands.command(name='auto-update-restart', description='Reboot AutoUpdate cog (admin only)')
    @commands.has_permissions(administrator=True)
    async def auto_update_restart(self, interaction: discord.Interaction):
        self.log.req(interaction.user, '', interaction.command.name)
        cog = self.bot.get_cog('AutoUpdate')
        await self.restart_cog()
        await interaction.response.send_message(content=f'AutoUpdate has been started!', ephemeral=True)

    async def restart_cog(self):
        cog = self.bot.get_cog('AutoUpdate')
        if cog is not None:
            await self.bot.remove_cog('AutoUpdate')
            await self.bot.add_cog(AutoUpdate(self.leaderboard_channel, self.queue_channel,
                                              self.twitch_channel, self.bot, self.db, self.ac))
        else:
            await self.bot.add_cog(AutoUpdate(self.leaderboard_channel, self.queue_channel,
                                              self.twitch_channel, self.bot, self.db, self.ac))


class Commands(commands.Cog):
    def __init__(self, twitch_channel, bot: DiscordBot, db: DB, spot: Spotify, ac: AudioController):
        self.ac = ac
        self.db = db
        self.bot = bot
        self.spot = spot
        self.log = self.bot.log
        self.twitch_channel = twitch_channel

    @staticmethod
    def has_role(role_names, ctx):
        roles = ctx.user.roles
        for role in roles:
            role = str(role)
            if type(role_names) is str:
                if role == role_names:
                    return True
            elif type(role_names) is list:
                if role in role_names:
                    return True
        return False

    @discord.app_commands.command(name='reset-leaderboard', description='Resets song request leaderboard so all '
                                                                        'requests have 0 rates and 0 requests. '
                                                                        '(channel admin only)')
    @commands.has_permissions(administrator=True)
    async def reset_leaderboard(self, interaction: discord.Interaction):
        self.log.req(interaction.user, '', interaction.command.name)

        if not self.has_role('DJ', interaction):
            resp = "You don't have the correct role to use this feature!"
            await interaction.response.send_message(content=resp, ephemeral=True)
            self.log.resp(resp)
            return None

        self.db.reset_all_user_stats()
        resp = "The leaderboard has been reset!"
        await interaction.response.send_message(content=resp, ephemeral=True)
        self.log.resp(resp)

    @discord.app_commands.command(name='stats', description='Gets song request stats of given twitch user.')
    @discord.app_commands.describe(twitch_username='Enter twitch username (not case sensitive)')
    async def get_stats(self, interaction: discord.Interaction, twitch_username: str):
        self.log.req(interaction.user, twitch_username, twitch_username)

        twitch_username = twitch_username.lower()
        try:
            stats = self.db.get_user_stats(twitch_username)
            if stats is None:
                self.log.error(
                    f'stats er: User {twitch_username} not found in database')
                await interaction.response.send_message(content=f'User not found.', ephemeral=True)
                return None

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
        except (ValueError, KeyError) as err:
            self.log.error(f'stats er: {err}')
            await interaction.response.send_message(content=f'User not found.', ephemeral=True)

    @discord.app_commands.command(name='remove-request', description='Remove song request from queue display'
                                  'by track name. (admin only)')
    @commands.has_permissions(administrator=True)
    @discord.app_commands.describe(req_id='enter request id')
    async def remove_request(self, interaction: discord.Interaction, req_id: int):
        self.log.req(interaction.user, str(req_id), interaction.command.name)

        if not self.has_role('DJ', interaction):
            resp = "You don't have the correct role to use this feature!"
            await interaction.response.send_message(content=resp, ephemeral=True)
            self.log.resp(resp)
            return None

        track, artist = self.db.remove_from_queue_by_id(req_id)
        if track is not None:
            await interaction.response.send_message(content=f'removed "{track} by {artist}" from queue', ephemeral=True)
        else:
            await interaction.response.send_message(content=f'Could not find id: "{req_id}" in queue', ephemeral=True)

    @discord.app_commands.command(name='clear-queue', description='Clear request queue display (admin only)')
    async def clear_queue(self, interaction: discord.Interaction):
        self.log.req(interaction.user, '', interaction.command.name)

        if not self.has_role('DJ', interaction):
            resp = "You don't have the correct role to use this feature!"
            await interaction.response.send_message(content=resp, ephemeral=True)
            self.log.resp(resp)
            return None

        self.db.clear_queue()
        resp = f'Queue has been cleared!'
        await interaction.response.send_message(content=resp, ephemeral=True)
        self.log.resp(resp)

    @discord.app_commands.command(name='queue', description='add a track to queue')
    @discord.app_commands.describe(request='enter request')
    @discord.ext.commands.has_role('DJ')
    async def queue(self, interaction: discord.Interaction, request: str):
        user = str(interaction.user)
        self.log.req(user, request, interaction.command.name)

        if not self.has_role('DJ', interaction):
            resp = "You don't have the correct role to use this feature!"
            await interaction.response.send_message(content=resp, ephemeral=True)
            self.log.resp(resp)
            return None

        track, artist = self.ac.add_to_queue(request, user)
        if track:
            resp = f'Added {track} by {artist} to the queue!'
        else:
            resp = f'Track not found'
        await interaction.response.send_message(content=resp, ephemeral=True)
        self.log.resp(resp)
        return None

    @discord.app_commands.command(name='bump', description='Moves a track to the top of the queue ')
    @discord.app_commands.describe(request_id='end the request id of the track')
    @commands.has_role('DJ')
    async def bump(self, interaction: discord.Interaction, request_id: int):
        user = str(interaction.user)
        self.log.req(user, str(request_id), interaction.command.name)

        if not self.has_role('DJ', interaction):
            resp = "You don't have the correct role to use this feature!"
            await interaction.response.send_message(content=resp, ephemeral=True)
            self.log.resp(resp)
            return None

        if self.db.move_request_pos(request_id):
            resp = f'Track moved to top of the queue'
        else:
            resp = f'Could not find track in queue'
        await interaction.response.send_message(content=resp, ephemeral=True)
        self.log.resp(resp)

    @queue.error
    async def cog_command_error(self, context: discord.Interaction, error) -> None:
        error = error.__cause__
        if isinstance(error, commands.errors.CommandOnCooldown):
            resp = str(error)
            await context.response.send_message(content=resp, ephemeral=True)
            self.log.resp(resp)

        elif isinstance(error, TrackAlreadyInQueue):
            resp = f'{error.track} by {error.artist} is already in the queue!'
            await context.response.send_message(content=resp, ephemeral=True)
            self.log.resp(resp)

        elif isinstance(error, NotActive):
            resp = f'Song request are currently turned off.'
            await context.response.send_message(content=resp, ephemeral=True)
            self.log.resp(resp)

        elif isinstance(error, YoutubeLink):
            resp = "Youtube support is coming soon!"
            await context.response.send_message(content=resp, ephemeral=True)
            self.log.resp(resp)

        elif isinstance(error, UnsupportedLink):
            resp = "Please only use spotify links!"
            await context.response.send_message(content=resp, ephemeral=True)
            self.log.resp(resp)

        else:
            traceback.print_exception(
                type(error), error, error.__traceback__, file=sys.stderr)
            self.log.error(error)
