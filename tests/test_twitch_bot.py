import unittest
import os
import sys
import time
path_src = os.path.abspath('./src')
sys.path.insert(1, path_src)
from utils import DB, Log, Settings, Creds
from utils.errors import *
from twitch.twitch_bot import TwitchBot
from twitch.public_online import OnlineCog
from twitch.mod import ModCog
from AudioController.audio_controller import AudioController, Context
from AudioController.spotify_api import Spotify


logger = Log('test', True, False)
creds = Creds(logger)
settings = Settings(logger)
db = DB(log=logger, db_path='./data/test.sqlite')


ac = AudioController(db, Spotify(creds.spotify), Context())

tb = TwitchBot(creds.twitch, logger, db, ac, settings)


class TestTwitchBot(unittest.TestCase):
    def setUp(self) -> None:
        db.delete_all()

    def test_add_veto(self):
        pc =  OnlineCog(tb)
        tb.settings.set_veto_pass(3)
        song_context1 = {"track": "track1", "artist": "artist1"}
        resp1, skip1 = pc.add_veto(song_context1, "vetouser1")
        self.assertFalse(skip1)
        self.assertEqual(
            f'1 out of 3 chatters have voted to skip the current song!', resp1)
        resp2, skip2 = pc.add_veto(song_context1, "vetouser1")
        self.assertFalse(skip2)
        self.assertEqual(
            f'You have already voted to veto the current song!', resp2)
        resp3, skip3 = pc.add_veto(song_context1, "vetouser2")
        self.assertFalse(skip3)
        self.assertEqual(
            f'2 out of 3 chatters have voted to skip the current song!', resp3)
        song_context2 = {"track": "track1", "artist": "artist2"}
        pc.add_veto(song_context2, 'vetouser1')
        pc.add_veto(song_context2, 'vetouser2')
        resp4, skip4 = pc.add_veto(song_context2, 'vetouser3')
        self.assertTrue(skip4)
        self.assertEqual(
            f'track1 by artist2 has been vetoed by chat LUL', resp4)

    def test_add_rates(self):
        pc = OnlineCog(tb)
        db.delete_user('requester1')
        db.delete_user('rategiver')
        db.init_user('requester1', requests=1)
        db.init_user('rategiver')
        song_context1 = {"playing_queue": True, "track": "track1",
                         "artist": "artist1", "requester": "requester1"}
        resp1 = pc.add_rate(song_context1, 'rategiver')
        self.assertEqual(
            f"@rategiver liked @requester1's song request!", resp1)
        stats1 = db.get_user_stats('requester1')
        self.assertEqual(1, stats1['rates'])
        stats2 = db.get_user_stats('rategiver')
        self.assertEqual(1, stats2['rates given'])
        resp2 = pc.add_rate(song_context1, 'rategiver')
        self.assertIsNone(resp2)
        resp3 = pc.add_rate(song_context1, 'requester1')
        self.assertEqual("Sorry, you can't rate your own requests LUL", resp3)
        db.delete_user('requester1')
        db.delete_user('rategiver')

    def test_ban_unban_user(self):
        mc = ModCog(tb)
        db.delete_user('tempmoduser')
        db.delete_user('tempbanuser')
        db.delete_user('tempuser')
        db.delete_user('tempmoduser2')
        db.init_user('tempmoduser', mod=1)
        db.init_user('tempbanuser')
        db.init_user('tempuser')
        db.init_user('tempmoduser2', mod=1)
        self.assertRaises(NotAuthorized, mc.ban, 'tempuser', 'tempbanuser')
        self.assertTrue(mc.ban('tempmoduser', 'tempbanuser'))
        self.assertTrue(db.is_user_banned('tempbanuser'))
        self.assertRaises(NotAuthorized, mc.ban, 'tempmoduser', 'tempmoduser2')
        self.assertRaises(NotAuthorized, mc.unban, 'tempuser', 'tempbanuser')
        self.assertTrue(mc.unban('tempmoduser', 'tempbanuser'))
        self.assertFalse(db.is_user_banned('tempbanuser'))

    def test_leaderboard_reset(self):
        db.delete_all()
        tb.settings.set_leaderboard_reset('weekly')
        db.init_user('previousWinner', mod=1, rates=1)
        now = int(time.time())
        week_ago = now - 604800
        db.add_leaderboard_winner('previousWinner', week_ago, now-100, sp_mod_given=True)
        db.init_user('leader', rates=10)
        tb.check_reset_leaderboard()
        resets = db.get_all_resets()
        self.assertEqual('previousWinner', resets[0][1])
        self.assertEqual(0, resets[0][5])
        self.assertEqual('leader', resets[1][1])
        self.assertEqual(1, resets[1][5])
        self.assertAlmostEqual(now + 604800, resets[1][3], delta=20)
        self.assertTrue(db.is_user_mod('leader'))
        self.assertFalse(db.is_user_mod('previousWinner'))
        db.delete_all()
        db.init_user('leader', rates=10)
        db.init_user('previousWinner', mod=1, rates=1)
        db.add_leaderboard_winner('previousWinner', week_ago, now-100, sp_mod_given=True)
        tb.settings.set_leaderboard_reset('off')
        tb.check_reset_leaderboard()
        resets = db.get_all_resets()
        self.assertEqual(1, len(resets))
        self.assertEqual('previousWinner', resets[0][1])
        self.assertEqual(1, resets[0][5])
        self.assertTrue(db.is_user_mod('previousWinner'))
        self.assertFalse(db.is_user_mod('leader'))

    def tearDown(self) -> None:
        db.delete_all()

if __name__ == '__main__':
    unittest.main(verbosity=1)
