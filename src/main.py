import os
from AudioController.spotify_api import Spotify
from twitch.bot import Bot as TwitchBot
from disc.webhook import DiscordHook
from os.path import exists
from AudioController.audio_controller import AudioController, Context
from twitch.wrapper import Wrapper
from utils import Log, DB, Settings, Creds
import asyncio
from typing import Optional


def init_data_dir():
    if not exists('./data'):
        os.mkdir('./data')


async def start_twitch_bot(creds: Creds, settings: Settings, ctx: Context,
                           ac_log: Log,
                           loop: Optional[asyncio.AbstractEventLoop] = None):
    service = Wrapper(creds.twitch)

    db = DB()
    await db.connect()
    s_bot = Spotify(creds.spotify)

    twitch_channel = creds.twitch.channel.lower()
    await db.admin_user(twitch_channel)

    ac = AudioController(db, s_bot, ctx, ac_log)

    t_bot = TwitchBot(service, db, settings, ac, creds.twitch)
    if loop is None:
        loop = asyncio.get_event_loop()

    # loop.run_until_complete(t_bot.check_live())
    loop.create_task(t_bot.start())


async def start_discord_hook(creds: Creds, settings: Settings,
                             loop: Optional[asyncio.AbstractEventLoop] = None):
    disc_creds = creds.discord
    channel = creds.twitch.channel

    disc_log = Log('Discord', settings.log)

    if not (disc_creds.queue_webhook or disc_creds.leaderboard_webhook):
        disc_log.error('No Discord Webhooks Provided')
        return

    db = DB()
    await db.connect()

    discord_hook = DiscordHook(disc_creds.queue_webhook,
                               disc_creds.leaderboard_webhook,
                               db, channel, disc_log)
    if loop is None:
        loop = asyncio.get_event_loop()
    loop.create_task(discord_hook.update())


def main():
    try:
        init_data_dir()

        main_log = Log('Main', True)

        creds = Creds(main_log)
        settings = Settings()
        ctx = Context()

        ac_log = Log('AudioController')

        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.new_event_loop()
        loop.create_task(start_twitch_bot(creds, settings, ctx, ac_log))
        loop.create_task(start_discord_hook(creds, settings))
        loop.run_forever()
    except KeyboardInterrupt:
        print('Exiting')
        exit(0)


if __name__ == "__main__":
    main()
