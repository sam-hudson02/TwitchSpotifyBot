import json
import os
import threading as th
from logger import Log
from spotify_api import Spotify
from twitch_bot import TwitchBot
from discord_bot import DiscordBot
from os.path import exists
from db_handler import DB
from dotenv import load_dotenv
from pathlib import Path
from errors import *
from audio_controller import AudioController, Context


def init_log():
    if not exists('./data'):
        os.mkdir('./data')
    if not exists('./data/sbotify.log'):
        with open('./data/log.txt', 'w') as log_file:
            log_file.close()


def get_creds(log: Log):
    env_path = Path('./secret/conf.env')
    load_dotenv(env_path)
    creds = {
        'spotify client id': os.getenv('SPOTIFY_CLIENT_ID'),
        'spotify secret': os.getenv('SPOTIFY_SECRET'),
        'spotify username': os.getenv('SPOTIFY_USERNAME'),
        'twitch token': os.getenv('TWITCH_TOKEN'),
        'twitch channel': os.getenv('TWITCH_CHANNEL'),
        'discord token': os.getenv('DISCORD_TOKEN'),
        'discord queue channel id': os.getenv('DISCORD_QUEUE_CHANNEL_ID'),
        'discord leaderboard channel id': os.getenv('DISCORD_LEADERBOARD_CHANNEL_ID'),
    }
    for cred in creds.keys():
        if 'discord' not in cred:
            if creds[cred] is None:
                log.critical(f'{cred} missing! Not continuing.')
                raise NoCreds
    return creds


def get_settings():
    if not exists('./data'):
        os.mkdir('./data')
    if not exists('./data/app.sqlite'):
        with open('./data/app.sqlite', 'w') as db_file:
            db_file.close()
    if exists('./data/settings.json'):
        with open('./data/settings.json') as s_file:
            settings = json.load(s_file)
            try:
                active = bool(settings['active'])
                disc_bot_on = bool(settings['discord bot'])
                veto_pass = int(settings['veto pass'])
                log_active = bool(settings['log'])
                dev_mode = bool(settings['dev mode'])
                leaderboard_reset = settings['leaderboard reset']
                leaderboard_rewards = settings['leaderboard rewards']
                leaderboard_announce = bool(settings['leaderboard announce'])
                s_file.close()
                return settings
            except (KeyError, ValueError):
                json.dump({}, s_file)
                s_file.close()
    active = True
    disc_bot_on = False
    veto_pass = 5
    log_active = True
    dev_mode = False
    leaderboard_reset = 'off'
    leaderboard_rewards = []
    leaderboard_announce = False
    with open('./data/settings.json', 'w') as s_file:
        settings = {'active': int(active),
                    'discord bot': int(disc_bot_on),
                    'veto pass': veto_pass,
                    'log': int(log_active),
                    'dev mode': int(dev_mode),
                    'leaderboard reset': leaderboard_reset,
                    'leaderboard rewards': leaderboard_rewards,
                    'leaderboard announce': int(leaderboard_announce),}
        json.dump(settings, s_file, indent=4)
        s_file.close()
        return settings


def start_twitch_bot(db_log: Log, creds: dict, settings: dict, ctx: Context):
    twitch_log = Log('Twitch', bool(settings['log']))
    db = DB(db_log)
    s_bot = Spotify(creds['spotify username'],
                    creds['spotify client id'], creds['spotify secret'])
    db.check_user_exists(creds['twitch channel'].lower())
    db.admin_user(creds['twitch channel'].lower())
    ac = AudioController(db, s_bot, ctx)
    t_bot = TwitchBot(creds['twitch token'],
                      creds['twitch channel'], twitch_log, db, ac)
    t_bot.run()


def start_discord_bot(db_log: Log, creds: dict, settings: dict, ctx: Context):
    discord_log = Log('Discord', bool(settings['log']))
    db = DB(db_log)
    s_bot = Spotify(creds['spotify username'],
                    creds['spotify client id'], creds['spotify secret'])
    db.check_user_exists(creds['twitch channel'].lower())
    db.admin_user(creds['twitch channel'].lower())
    ac = AudioController(db, s_bot, ctx)
    d_bot = DiscordBot(creds['discord leaderboard channel id'], creds['discord queue channel id'],
                       creds['twitch channel'], discord_log, s_bot, db, ac)
    d_bot.run(creds['discord token'])


def check_if_discord(creds, log: Log):
    if creds.get('discord token') is None:
        log.info('Discord token not found, not starting Discord bot.')
        return False
    elif creds.get('discord leaderboard channel id') is None:
        log.info(
            'Discord leaderboard channel id not found, not starting Discord bot.')
        return False
    elif creds.get('discord queue channel id') is None:
        log.info('Discord queue channel id not found, not starting Discord bot.')
        return False
    elif creds.get('discord leaderboard channel id') == creds.get('discord queue channel id'):
        log.info(
            'Discord leaderboard channel id and Discord queue channel id are the same, not starting Discord bot.')
        return False
    else:
        return True


def main():
    init_log()
    main_log = Log('Main', True)

    creds = get_creds(main_log)
    settings = get_settings()

    db_log = Log('Database', bool(settings['log']))
    ctx = Context()
    if check_if_discord(creds, main_log):
        th.Thread(target=start_discord_bot, args=(
            db_log, creds, settings, ctx), daemon=True).start()
    start_twitch_bot(db_log, creds, settings, ctx)


if __name__ == "__main__":
    main()
