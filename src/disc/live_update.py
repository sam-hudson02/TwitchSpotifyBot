from table2ascii import table2ascii as t2a, PresetStyle
from discord.ext import tasks, commands
import discord


class AutoUpdate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log = bot.log
        self.settings = bot.settings
        self.ac = bot.ac
        self.spot = bot.spot
        self.db = bot.db
        self.leaderboard_channel = bot.get_channel(bot.leaderboard_channel_id)
        self.queue_channel = bot.get_channel(bot.queue_channel_id)
        self.context = None
        self.leaderboard_message_obj = None
        self.queue_message_obj = None
        self.playing_message_obj = None
        self.twitch_channel = bot.twitch_channel
        self.leaderboard = discord.Embed(
            title=f'{self.twitch_channel} Song Request Leaderboard')
        self.queue = []
    
    async def cog_load(self) -> None:
        self.log.info('AutoUpdate Cog Loaded')
        await self.get_message_obj_queue()
        await self.get_message_obj_leaderboard()
        
        self.get_queue.start()
        self.get_leaderboard.start()
        self.get_context.start()

    async def cog_unload(self) -> None:
        self.log.info('AutoUpdate Cog Unloaded')

        self.get_queue.cancel()
        self.get_leaderboard.cancel()
        self.get_context.cancel()

        await self.cleanup_playing()

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

        if len(q) == 0:
            return f"{self.twitch_channel} Song Request Queue: \n" \
                   f"```\nQueue is Currently Empty!\n```"

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

        if len(queue_content) < 2000:
            return queue_content
        else:
            return 'Problem with queue :/'

    async def cleanup_playing(self):
        if self.queue_message_obj is None:
            return
        
        queue = self.embed_queue()

        await self.queue_message_obj.edit(content=queue, embed=None, view=None)

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
    
    async def restart_cog(self):
        self.bot.remove_cog(self.__cog_name__)
        self.bot.add_cog(self(self.bot))
    
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
