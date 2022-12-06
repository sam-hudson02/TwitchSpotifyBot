import unittest
import src.db_handler as db_handler
from src.logger import Log
from dotenv import load_dotenv
from pathlib import Path
import os
from src.errors import *
from src.twitch_bot import TwitchBot
from src.audio_controller import AudioController
from spotify_api import Spotify


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
        'mysql host': os.getenv('MYSQL_HOST'),
        'mysql user': os.getenv('MYSQL_USER'),
        'mysql password': os.getenv('MYSQL_PASSWORD')
    }
    for cred in creds.keys():
        if creds[cred] is None:
            log.critical(f'{cred} missing! Not continuing.')
            raise NoCreds
    return creds


logger = Log('test', True, False)
creds = get_creds(logger)
db = db_handler.DB(log=logger, db_path='./data/test.sqlite')

ac = AudioController(db, Spotify(
    creds['spotify username'], creds['spotify client id'], creds['spotify secret']))

tb = TwitchBot(creds['twitch token'], creds['twitch channel'], logger, db, ac)


class TestTwitchBot(unittest.TestCase):
    def setUp(self) -> None:
        db.delete_all()

    def test_add_veto(self):
        tb.settings = {"veto pass": 3}
        song_context1 = {"track": "track1", "artist": "artist1"}
        resp1, skip1 = tb.add_veto(song_context1, "vetouser1")
        self.assertFalse(skip1)
        self.assertEqual(
            f'1 out of 3 chatters have voted to skip the current song!', resp1)
        resp2, skip2 = tb.add_veto(song_context1, "vetouser1")
        self.assertFalse(skip2)
        self.assertEqual(
            f'You have already voted to veto the current song!', resp2)
        resp3, skip3 = tb.add_veto(song_context1, "vetouser2")
        self.assertFalse(skip3)
        self.assertEqual(
            f'2 out of 3 chatters have voted to skip the current song!', resp3)
        song_context2 = {"track": "track1", "artist": "artist2"}
        tb.add_veto(song_context2, 'vetouser1')
        tb.add_veto(song_context2, 'vetouser2')
        resp4, skip4 = tb.add_veto(song_context2, 'vetouser3')
        self.assertTrue(skip4)
        self.assertEqual(
            f'track1 by artist2 has been vetoed by chat LUL', resp4)

    def test_add_rates(self):
        db.delete_user('requester1')
        db.delete_user('rategiver')
        db.init_user('requester1', requests=1)
        db.init_user('rategiver')
        song_context1 = {"playingQueue": True, "track": "track1",
                         "artist": "artist1", "requester": "requester1"}
        resp1 = tb.add_rate(song_context1, 'rategiver')
        self.assertEqual(
            f"@rategiver liked @requester1's song request!", resp1)
        stats1 = db.get_user_stats('requester1')
        self.assertEqual(1, stats1['rates'])
        stats2 = db.get_user_stats('rategiver')
        self.assertEqual(1, stats2['rates given'])
        resp2 = tb.add_rate(song_context1, 'rategiver')
        self.assertIsNone(resp2)
        resp3 = tb.add_rate(song_context1, 'requester1')
        self.assertEqual("Sorry, you can't rate your own requests LUL", resp3)
        db.delete_user('requester1')
        db.delete_user('rategiver')

    def test_ban_unban_user(self):
        db.delete_user('tempmoduser')
        db.delete_user('tempbanuser')
        db.delete_user('tempuser')
        db.delete_user('tempmoduser2')
        db.init_user('tempmoduser', mod=1)
        db.init_user('tempbanuser')
        db.init_user('tempuser')
        db.init_user('tempmoduser2', mod=1)
        self.assertRaises(NotAuthorized, tb.ban, 'tempuser', 'tempbanuser')
        self.assertTrue(tb.ban('tempmoduser', 'tempbanuser'))
        self.assertTrue(db.is_user_banned('tempbanuser'))
        self.assertRaises(NotAuthorized, tb.ban, 'tempmoduser', 'tempmoduser2')
        self.assertRaises(NotAuthorized, tb.unban, 'tempuser', 'tempbanuser')
        self.assertTrue(tb.unban('tempmoduser', 'tempbanuser'))
        self.assertFalse(db.is_user_banned('tempbanuser'))


if __name__ == '__main__':
    unittest.main(verbosity=1)
