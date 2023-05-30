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
if TYPE_CHECKING:
    from twitch.cog import Cog


class Bot:
    def __init__(self, service: Wrapper, db: DB, settings: Settings,
                 ac: AudioController, creds: TwitchCreds, prefix: str = '!'):
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
        print('joined ' + channel)
        await self.service.send('Sbotify is now online!')

    async def on_message(self, msg: Message) -> None:
        try:
            print(msg.content)
            if msg.content.startswith(self.prefix):
                print(msg.content)
                command = msg.content[len(self.prefix):].split(' ')[0]
                await self.router.handle(msg, command)
        except Exception as e:
            await self.on_error(msg, e)

    async def start(self):
        print('loading cogs')
        await self.load_cogs()
        print('starting bot')
        await self.service.start()

    async def load_cogs(self):
        for cog in self.cogs:
            await cog.load()

    async def on_error(self, msg: Message, error: Exception):
        print(error)
        await msg.reply('An error occurred!')

    def __del__(self):
        self.service.disconnect()
