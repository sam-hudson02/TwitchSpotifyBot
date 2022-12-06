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
from audio_controller import AudioController


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
        if creds[cred] is None:
            log.critical(f'{cred} missing! Not continuing.')
            raise NoCreds
    return creds


def get_settings():
    if exists('./data/settings.json'):
        with open('./data/settings.json') as s_file:
            settings = json.load(s_file)
            try:
                active = bool(settings['active'])
                disc_bot_on = bool(settings['discord bot'])
                veto_pass = settings['veto pass']
                log_active = bool(settings['log'])
                dev_mode = bool(settings['dev mode'])
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
    with open('./data/settings.json', 'w') as s_file:
        settings = {'active': int(active),
                    'discord bot': int(disc_bot_on),
                    'veto pass': veto_pass,
                    'log': int(log_active),
                    'dev mode': int(dev_mode)}
        json.dump(settings, s_file)
        s_file.close()
        return settings


def start_twitch_bot(db_log: Log, creds: dict, settings: dict):
    twitch_log = Log('Twitch', bool(settings['log']))
    db = DB(db_log)
    s_bot = Spotify(creds['spotify username'],
                    creds['spotify client id'], creds['spotify secret'])
    db.check_user_exists(creds['twitch channel'].lower())
    db.admin_user(creds['twitch channel'].lower())
    ac = AudioController(db, s_bot)
    t_bot = TwitchBot(creds['twitch token'],
                      creds['twitch channel'], twitch_log, db, ac)
    t_bot.run()


def start_discord_bot(db_log: Log, creds: dict, settings: dict):
    discord_log = Log('Discord', bool(settings['log']))
    db = DB(db_log)
    s_bot = Spotify(creds['spotify username'],
                    creds['spotify client id'], creds['spotify secret'])
    db.check_user_exists(creds['twitch channel'].lower())
    db.admin_user(creds['twitch channel'].lower())
    ac = AudioController(db, s_bot)
    d_bot = DiscordBot(creds['discord leaderboard channel id'], creds['discord queue channel id'],
                       creds['twitch channel'], discord_log, s_bot, db, ac)
    d_bot.run(creds['discord token'])


def main():
    main_log = Log('Main', True)

    creds = get_creds(main_log)
    settings = get_settings()

    db_log = Log('Database', bool(settings['log']))

    th.Thread(target=start_twitch_bot, args=[db_log, creds, settings]).run()

    if bool(settings['discord bot']):
        th.Thread(target=start_discord_bot, args=[
                  db_log, creds, settings]).run()


if __name__ == "__main__":
    main()
