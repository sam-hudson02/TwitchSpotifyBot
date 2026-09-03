import asyncio
from utils import Log, DB, DiscordCreds
from disc.webhook import DiscordHook


class DiscordInitial:
    def __init__(self, loop: asyncio.AbstractEventLoop, creds: DiscordCreds,
                 channel: str):
        self.log: Log = Log('DiscordInit', file='./data/discord_init.log')
        self.creds: DiscordCreds = creds
        self.channel: str = channel
        self.loop: asyncio.AbstractEventLoop = loop
        self.db: DB = DB()
        self.hook: DiscordHook | None = None

    async def start_hook(self) -> bool:
        if not (self.creds.queue_webhook or self.creds.leaderboard_webhook):
            self.log.error('No Discord Webhooks Provided')
            return False

        self.log.info('Starting Discord Hook')
        try:
            await self.db.connect()
            self.hook = DiscordHook(self.creds.queue_webhook,
                                    self.creds.leaderboard_webhook,
                                    self.db, self.channel, self.log)
            if self.loop is None:
                self.loop = asyncio.get_running_loop()

            self.loop.create_task(self.hook.update())
            return True

        except Exception as e:
            self.log.error(f'Failed to start Discord Hook: {e}')
            return False

    async def stop_hook(self) -> bool:
        self.log.info('Stopping Discord Hook')
        try:
            if self.hook is not None:
                await self.hook.cleanup()
            if self.db is not None:
                await self.db.disconnect()
            return True
        except Exception as e:
            self.log.error(f'Failed to stop Discord Hook: {e}')
            return False
