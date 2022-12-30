import os
import threading as th
from spotify_api import Spotify
from twitch.main import TwitchBot
from discord_bot import DiscordBot
from os.path import exists
from utils.errors import *
from audio_controller import AudioController, Context
from utils import Log, DB, Settings, Creds


def init_data_dir():
    if not exists('./data'):
        os.mkdir('./data')


def start_twitch_bot(db_log: Log, creds: Creds, settings: Settings, ctx: Context):
    twitch_log = Log('Twitch', settings.get_log())

    db = DB(db_log)
    s_bot = Spotify(creds.spotify)

    twitch_channel = creds.twitch.channel.lower()

    db.check_user_exists(twitch_channel)
    db.admin_user(twitch_channel)

    ac = AudioController(db, s_bot, ctx)

    t_bot = TwitchBot(creds.twitch, twitch_log, db, ac, settings)
    t_bot.run()


def start_discord_bot(db_log: Log, creds: Creds, settings: Settings, ctx: Context):
    discord_log = Log('Discord', settings.get_log())

    db = DB(db_log)
    s_bot = Spotify(creds.spotify)

    ac = AudioController(db, s_bot, ctx)

    d_bot = DiscordBot(creds.discord, creds.twitch.channel, discord_log, s_bot, db, ac)
    d_bot.run(creds.discord.token)


def main():
    init_data_dir()

    main_log = Log('Main', True)

    creds = Creds(main_log)
    settings = Settings(main_log)
    ctx = Context()

    db_log = Log('Database', settings.get_log())

    if creds.discord.creds_valid() and settings.get_discord_bot():
        th.Thread(target=start_discord_bot, args=(
            db_log, creds, settings, ctx), daemon=True).start()
    start_twitch_bot(db_log, creds, settings, ctx, settings)


if __name__ == "__main__":
    main()
