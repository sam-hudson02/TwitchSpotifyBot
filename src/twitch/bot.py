import asyncio
import socket as socket_module
from typing import TYPE_CHECKING, Optional

from AudioController.audio_controller import AudioController
from twitch.wrapper import Message, Wrapper
from twitch.router import Router
from twitch.public_online import OnlineCog
from twitch.public_offline import OfflineCog
from twitch.mod import ModCog
from twitch.admin import AdminCog
from utils.command_config import CommandConfig
from utils.logger import Log
from services import Services, TwitchInterface
if TYPE_CHECKING:
    from twitch.cog import Cog


class Bot(TwitchInterface):
    def __init__(self, services: Services,
                 socket: Optional[socket_module.socket] = None,
                 prefix: str = '!'):
        self.log = Log('Twitch')
        self.creds = services.creds.twitch
        self.channel: str = self.creds.channel
        self.settings = services.settings
        self.db = services.db
        self.context = services.context
        self.service: Wrapper = Wrapper(self.creds, socket)
        self.service.on_join(self.on_join)
        self.service.on_message(self.on_message)
        self.router: Router = Router(self)
        self.commands: CommandConfig = CommandConfig()
        self.prefix: str = prefix
        self.ac: AudioController = AudioController(self.db, services.spotify,
                                                  self.context,
                                                  Log('AudioController'))
        self.cogs: list['Cog'] = [OnlineCog(self),
                                  OfflineCog(self),
                                  ModCog(self),
                                  AdminCog(self)]

    async def start(self) -> None:
        self.log.info('Starting Twitch bot')
        await self.db.admin_user(self.channel.lower())
        await self.load_cogs()
        await self.service.start()
        await self.start_routines()

    async def stop(self) -> None:
        self.log.info('Stopping service')
        await self.service.cleanup()
        self.log.info('Stopping routines')
        if hasattr(self, 'check_live_routine'):
            self.check_live_routine.cancel()
        if hasattr(self, 'ac_update_routine'):
            self.ac_update_routine.cancel()

    async def on_join(self, channel: str) -> None:
        self.log.info(f'Joined channel: {channel}')
        await self.service.send(self.commands.message('GENERAL', 'online'))

    async def on_message(self, msg: Message) -> None:
        try:
            if msg.content.startswith(self.prefix):
                command = msg.content[len(self.prefix):].split(' ')[0]
                await self.router.handle(msg, command)
        except Exception as e:
            await self.on_error(msg, e)

    async def on_live(self):
        self.log.info(f'{self.channel} is live!')

    async def load_cogs(self):
        for cog in self.cogs:
            await cog.load()

    async def on_error(self, msg: Message, error: Exception):
        self.log.error(f'Error: {error}')
        await msg.reply(self.commands.message('GENERAL', 'error'))

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
        loop = asyncio.get_running_loop()
        self.check_live_routine = loop.create_task(self.check_live())
        self.ac_update_routine = loop.create_task(self.ac.update())

    async def skip(self):
        await self.ac.play_next(skipped=True)

    async def add_song(self, query: str, requester: str):
        return await self.ac.add_to_queue(query, requester)
