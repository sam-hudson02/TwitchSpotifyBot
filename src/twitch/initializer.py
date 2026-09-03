import asyncio
from AudioController.spotify_api import Spotify
from utils import Log, DB, Settings, TwitchCreds
from twitch.bot import Bot as TwitchBot
from AudioController.audio_controller import AudioController, Context
from twitch.wrapper import Wrapper

class TwitchInitial:
    def __init__(self, loop: asyncio.AbstractEventLoop, creds: TwitchCreds, settings: Settings, 
                 spotify: Spotify):
        self.log: Log = Log('TwitchInit', file='./data/twitch_init.log')
        self.ctx: Context = Context()
        self.settings: Settings = settings
        self.creds: TwitchCreds = creds
        self.channel: str = self.creds.channel.lower()
        self.loop: asyncio.AbstractEventLoop = loop
        self.service = Wrapper(self.creds)
        self.db = DB()
        self.spotify: Spotify = spotify
        self.ac: AudioController = AudioController(self.db, self.spotify,
                                                  self.ctx, self.log)
        self.bot: TwitchBot = TwitchBot(self.service, self.db, self.settings,
                                        self.ac, self.creds)

    async def start_bot(self) -> bool:
        self.log.info('Starting Twitch Bot')
        try:
            await self.db.connect()
            await self.db.admin_user(self.channel)
            if self.loop is None:
                self.loop = asyncio.get_running_loop()

            # loop.run_until_complete(t_bot.check_live())
            self.loop.create_task(self.bot.start())

            return True

        except Exception as e:
            self.log.error(f'Failed to start Twitch Bot: {e}')
            return False

    async def stop_bot(self) -> bool:
        self.log.info('Stopping Twitch Bot')
        try:
            if self.bot is not None:
                await self.bot.stop()
            if self.db is not None:
                await self.db.disconnect()
            return True
        except Exception as e:
            self.log.error(f'Failed to stop Twitch Bot: {e}')
            return False
