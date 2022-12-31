import discord 
import time
from AudioController.spotify_api import Spotify
from discord.ext import tasks, commands
from AudioController.audio_controller import AudioController
from utils import Log, DB, Settings, DiscordCreds
from utils.errors import *
from disc.public import PublicCog
from disc.live_update import AutoUpdate
from disc.mod import ModCog
from disc.admin import AdminCog

class DiscordBot(commands.Bot):
    def __init__(self, creds: DiscordCreds, twitch_channel, log: Log,
                 spot: Spotify, db: DB, ac: AudioController, settings: Settings):
        super().__init__('/', intents=discord.Intents.default())
        self.ac = ac
        self.log = log
        self.settings = settings
        self.spot = spot
        self.db = db
        leaderboard_channel_id = creds.leaderboard_channel_id
        queue_channel_id = creds.queue_channel_id
        self.leaderboard_channel_id = int(leaderboard_channel_id)
        self.queue_channel_id = int(queue_channel_id)
        self.twitch_channel = twitch_channel
        self.online_cogs = [AutoUpdate]
        self.offline_cogs = [PublicCog, ModCog, AdminCog]
        self.is_live = False

    @tasks.loop(seconds=5)
    async def check_live(self):
        if self.is_live == self.ac.context.live:
            return
        
        self.is_live = self.ac.context.live
        if self.is_live:
            await self.load_online_cogs()
        else:
            await self.unload_online_cogs()
        await self.tree.sync()

    async def on_ready(self) -> None:
        self.log.info('Discord bot listening.')
        await self.load_cogs()
        await self.tree.sync()
        self.check_live.start()
    
    async def on_disconnect(self):
        self.log.info('Bot disconnected.')
        while self.is_closed():
            time.sleep(5)
            self.log.info('Bot attempting reconnecting.')
        if not self.is_closed():
            self.log.info('Bot reconnected. Reloading cogs.')
            await self.reload_cogs()
            await self.restart_tasks()

    async def reload_cogs(self):
        await self.unload_cogs()
        await self.load_cogs()
        await self.tree.sync()

    async def load_cogs(self):
        await self.load_online_cogs()
        await self.load_offline_cogs()
    
    async def load_online_cogs(self):
        unload_cogs = [cog for cog in self.online_cogs if cog.__cog_name__ not in self.cogs.keys()]
        if not self.ac.context.live:
            return
        for cog in unload_cogs:
            await self.add_cog(cog(self))
    
    async def load_offline_cogs(self):
        unload_cogs = [cog for cog in self.offline_cogs if cog.__cog_name__ not in self.cogs.keys()]
        for cog in unload_cogs:
            await self.add_cog(cog(self))

    async def unload_cogs(self):
        loaded_cogs = [cog for cog in self.cogs.keys()]
        for cog in loaded_cogs:
            await self.remove_cog(cog)
    
    async def unload_online_cogs(self):
        cog_names = [cog.__cog_name__ for cog in self.online_cogs]
        loaded_cogs = [cog for cog in self.cogs.keys()]
        for cog in cog_names:
            if cog in loaded_cogs:
                await self.remove_cog(cog)

    async def restart_tasks(self):
        if self.check_live.is_running():
            self.check_live.restart()
        else:
            self.check_live.start()

    