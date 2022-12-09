import unittest
import os
import sys
path_src = os.path.abspath('./src')
sys.path.insert(1, path_src)
import db_handler as db_handler
from logger import Log
from errors import *

logger = Log('test', True, False)
db = db_handler.DB(log=logger, db_path='./data/test.sqlite')


class TestDbHandler(unittest.TestCase):
    def setUp(self) -> None:
        db.delete_all()

    def test_db_user_create_delete_functions(self):
        db.delete_user('testUser')
        self.assertTrue(db.init_user('testUser'))
        self.assertTrue(db.check_user_exists('testUser'))
        self.assertFalse(db.check_user_exists('testUserTemp'))
        self.assertTrue(db.delete_user('testUserTemp'))

    def test_db_user_attributes(self):
        db.init_user('bannedUser', ban=1)
        db.init_user('modUser', mod=1)
        db.init_user('adminUser', admin=1)
        db.init_user('10ratesUser', rates=10)

        self.assertTrue(db.is_user_banned("bannedUser"))
        self.assertTrue(db.is_user_mod("modUser"))
        self.assertTrue(db.is_user_admin("adminUser"))
        self.assertTrue(db.is_user_privileged("modUser"))
        self.assertTrue(db.is_user_admin("adminUser"))
        self.assertFalse(db.is_user_mod("bannedUser"))
        self.assertFalse(db.is_user_admin("bannedUser"))
        self.assertFalse(db.is_user_privileged("bannedUser"))
        stats = db.get_user_stats('10ratesUser')
        self.assertEqual(1, stats['pos'])
        self.assertEqual(10, stats['rates'])
        self.assertEqual(0, stats['rates given'])
        self.assertEqual(0, stats['requests'])

    def test_db_user_add_remove_attributes(self):
        db.delete_user('tempUser')
        db.delete_user('tempUserGiver')
        db.init_user('tempUser')
        db.init_user('tempUserGiver')
        db.add_rate('tempUser', 'tempUserGiver')
        db.mod_user('tempUser')
        db.admin_user('tempUser')
        stats_rec = db.get_user_stats('tempUser')
        stats_giver = db.get_user_stats('tempUserGiver')
        self.assertEqual(1, stats_rec['rates'])
        self.assertEqual(1, stats_giver['rates given'])
        self.assertTrue(db.is_user_mod('tempUser'))
        self.assertTrue(db.is_user_admin('tempUser'))
        self.assertTrue(db.is_user_privileged('tempUser'))
        db.ban_user('tempUser')
        self.assertTrue(db.is_user_banned('tempUser'))
        self.assertFalse(db.is_user_admin('tempUser'))
        self.assertFalse(db.is_user_mod('tempUser'))
        self.assertFalse(db.is_user_privileged('tempUser'))
        db.unban_user('tempUser')
        self.assertFalse(db.is_user_banned('tempUser'))
        db.delete_user('tempUser')
        db.delete_user('tempUserGiver')

    def test_queue(self):
        q1 = db.get_queue()
        if len(q1) > 0:
            db.clear_queue()
        self.assertEqual(db.get_queue(), [])
        db.add_to_queue('requester', 'track1', 'link', 'artist')
        db.add_to_queue('requester', 'track2', 'link', 'artist')
        db.add_to_queue('requester', 'track3', 'link', 'artist')
        track1_id = db.get_req_id_by_track_name('track1')
        track2_id = db.get_req_id_by_track_name('track2')
        track3_id = db.get_req_id_by_track_name('track3')
        expected_queue1 = [(track1_id, 1, 'track1', 'artist', 'requester', 'link'),
                           (track2_id, 2, 'track2', 'artist',
                            'requester', 'link'),
                           (track3_id, 3, 'track3', 'artist', 'requester', 'link')]
        self.assertEqual(expected_queue1, db.get_queue())
        db.move_request_pos(track1_id, 3)
        expected_queue2 = [(track2_id, 1, 'track2', 'artist', 'requester', 'link'),
                           (track3_id, 2, 'track3', 'artist',
                            'requester', 'link'),
                           (track1_id, 3, 'track1', 'artist', 'requester', 'link')]
        self.assertEqual(expected_queue2, db.get_queue())
        db.remove_from_queue_by_id(track3_id)
        expected_queue3 = [(track2_id, 1, 'track2', 'artist', 'requester', 'link'),
                           (track1_id, 2, 'track1', 'artist', 'requester', 'link')]
        self.assertEqual(expected_queue3, db.get_queue())
        self.assertTrue(db.is_track_in_queue('track1', 'artist'))
        db.clear_queue()
        self.assertEqual([], db.get_queue())
        self.assertIsNone(db.get_req_id_by_track_name('NotATrack'))

    def tearDown(self) -> None:
        db.delete_all()

if __name__ == '__main__':
    unittest.main(verbosity=1)
