from disc.webhook import DiscordHook
from utils import Creds, DB, Log
import unittest


class TestDiscord(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        creds = Creds()
        queue_url = creds.discord.queue_webhook
        leaderboard_url = creds.discord.leaderboard_webhook
        self.db = DB()
        await self.db.connect()
        log = Log('Discord')
        self.channel = creds.twitch.channel
        self.hook = DiscordHook(queue_url, leaderboard_url, self.db,
                                self.channel, log)
        await self.db_reset()

    async def db_reset(self):
        await self.db.delete_all()
        await self.db.get_user(self.channel, True, True)

    async def add_rate(self, user, num=1):
        for _ in range(num):
            await self.db.add_rate(user, self.channel)

    async def testLeaderboard(self):
        await self.db_reset()

        # add 3 users to the db
        await self.db.get_user('user1', False, False)
        await self.db.get_user('user2', False, False)
        await self.db.get_user('user3', False, False)

        # add 1 rate to user1, 2 to user2, 3 to user3
        await self.add_rate('user1', 1)
        await self.add_rate('user2', 2)
        await self.add_rate('user3', 3)

        # check the leaderboard
        leaderboard = await self.db.get_leaderboard()
        embed = await self.hook.embed_leaderboard(leaderboard)
        expected_title = f'{self.channel}\'s Song Request Leaderboard'
        self.assertEqual(embed.title, expected_title)
        self.assertEqual(embed.fields[0].name, 'Position')
        self.assertEqual(embed.fields[0].value, '1\n2\n3\n4')
        self.assertEqual(embed.fields[1].name, 'User')
        self.assertEqual(embed.fields[1].value,
                         f'user3\nuser2\nuser1\n{self.channel}')
        self.assertEqual(embed.fields[2].name, 'Rates')
        self.assertEqual(embed.fields[2].value, '3\n2\n1\n0')
