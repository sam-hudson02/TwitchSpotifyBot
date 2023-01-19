import os
import threading as th
from AudioController.spotify_api import Spotify
from twitch.twitch_bot import TwitchBot
from disc.discord_bot import DiscordBot
from os.path import exists
from utils.errors import *
from AudioController.audio_controller import AudioController, Context
from utils import Log, DB, Settings, Creds


def init_data_dir():
    if not exists('./data'):
        os.mkdir('./data')


def start_twitch_bot(db_log: Log, creds: Creds, settings: Settings, ctx: Context, ac_log: Log):
    twitch_log = Log('Twitch', settings.log)

    db = DB(db_log)
    s_bot = Spotify(creds.spotify)

    twitch_channel = creds.twitch.channel.lower()

    db.check_user_exists(twitch_channel)
    db.admin_user(twitch_channel)

    ac = AudioController(db, s_bot, ctx, ac_log)

    t_bot = TwitchBot(creds.twitch, twitch_log, db, ac, settings)
    t_bot.run()


def start_discord_bot(db_log: Log, creds: Creds, settings: Settings, ctx: Context, ac_log: Log):
    discord_log = Log('Discord', settings.log)

    db = DB(db_log)
    s_bot = Spotify(creds.spotify)

    ac = AudioController(db, s_bot, ctx, ac_log)

    d_bot = DiscordBot(creds.discord, creds.twitch.channel, discord_log, s_bot, db, ac, settings)
    d_bot.run(creds.discord.token)


def main():
    init_data_dir()

    main_log = Log('Main', True)

    creds = Creds(main_log)
    settings = Settings()
    ctx = Context()

    # Database log is used for both twitch and discord bots DB instances
    # Database not initialized in main function as it cannot be shared between threads
    db_log = Log('Database', settings.log)
    ac_log = Log('AudioController', settings.log)

    if creds.discord.creds_valid() and settings.discord_bot:
        th.Thread(target=start_discord_bot, args=(
            db_log, creds, settings, ctx, ac_log), daemon=True).start()
    start_twitch_bot(db_log, creds, settings, ctx, ac_log)


if __name__ == "__main__":
    main()
