import asyncio
from AudioController.audio_controller import AudioController
from twitch.wrapper import Message, Wrapper
from typing import TYPE_CHECKING
from utils.creds import TwitchCreds
from utils.db import DB
from utils.settings import Settings
from twitch.router import Router
from twitch.public_online import OnlineCog
from twitch.public_offline import OfflineCog
from twitch.mod import ModCog
from twitch.admin import AdminCog
from utils.logger import Log
if TYPE_CHECKING:
    from twitch.cog import Cog


class Bot:
    def __init__(self, service: Wrapper, db: DB, settings: Settings,
                 ac: AudioController, creds: TwitchCreds, prefix: str = '!'):
        self.log = Log('Twitch')
        self.service: Wrapper = service
        self.service.on_join(self.on_join)
        self.service.on_message(self.on_message)
        self.channel: str = creds.channel
        self.router: Router = Router(self)
        self.settings: Settings = settings
        self.prefix: str = prefix
        self.db: DB = db
        self.ac: AudioController = ac
        self.cogs: list['Cog'] = [OnlineCog(self),
                                  OfflineCog(self),
                                  ModCog(self),
                                  AdminCog(self)]

    async def on_join(self, channel: str) -> None:
        self.log.info(f'Joined channel: {channel}')
        await self.service.send('Sbotify is now online!')

    async def on_message(self, msg: Message) -> None:
        try:
            if msg.content.startswith(self.prefix):
                command = msg.content[len(self.prefix):].split(' ')[0]
                await self.router.handle(msg, command)
        except Exception as e:
            await self.on_error(msg, e)

    async def on_live(self):
        self.log.info(f'{self.channel} is live!')

    async def start(self):
        self.log.info('Loading cogs')
        await self.load_cogs()
        self.log.info('Starting service')
        await self.service.start()
        await self.start_routines()

    async def load_cogs(self):
        for cog in self.cogs:
            await cog.load()

    async def on_error(self, msg: Message, error: Exception):
        await msg.reply('An error occurred!')

    async def check_live(self):
        while True:
            live = await self.service.api.is_live()
            if self.settings.dev_mode:
                live = True
            if live and not self.ac.context.live:
                self.log.info(f'{self.channel} is live!')
                self.ac.context.live = True
            elif not live and self.ac.context.live:
                self.log.info(f'{self.channel} is offline!')
                self.ac.context.live = False
            await asyncio.sleep(10)

    async def start_routines(self):
        loop = asyncio.get_event_loop()
        self.check_live_routine = loop.create_task(self.check_live())
        self.ac_update_routine = loop.create_task(self.ac.update())
