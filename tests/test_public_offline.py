import unittest
from utils.settings import Settings
from utils.logger import Log
from utils.db import DB
from utils.creds import Creds
from twitch.bot import Bot
from AudioController.audio_controller import Context
from services import Services
from mocks.mock_sock import MockSocket
from mocks.mock_spot import MockSpot
import random

from utils.types import SongReq
# add src to path


class TestPublicOnline(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.creds = Creds()
        self.socket = MockSocket(self.creds)
        self.db = DB()
        await self.db.connect()
        await self.db.delete_all()
        self.channel = self.creds.twitch.channel
        await self.db.get_user(self.channel, True, True)
        self.spot = MockSpot()
        self.audio_ctx = Context()
        self.settings = Settings()
        services = Services(creds=self.creds, settings=self.settings,
                            db=self.db, spotify=self.spot,
                            context=self.audio_ctx)
        self.bot = Bot(services, socket=self.socket)
        self.wrapper = self.bot.service
        self.ac = self.bot.ac
        await self.bot.load_cogs()
        print('setup complete')

    async def asyncTearDown(self):
        await self.reset_db()

    async def reset_db(self):
        await self.db.delete_all()
        await self.db.get_user(self.channel, True, True)

    async def testHelp(self):
        self.socket.from_twitch('!help', self.channel, self.channel)
        await self.wrapper.read()
        expected_start = f'@{self.channel} A list of commands can be found here'
        last = self.socket.get_last()
        print(last)
        self.assertEqual(expected_start, last)

    async def add_rate(self, user, num=1):
        for _ in range(num):
            await self.db.add_rate(user, self.channel)

    async def add_request(self, user, num=1):
        for _ in range(num):
            # generate random SongRequest
            name = f'random_song_{random.randint(0, 1000)}'
            aritst = f'random_artist_{random.randint(0, 1000)}'
            url = f'random_url_{random.randint(0, 1000)}'
            requester = user
            song_request = SongReq(name, aritst, url, requester)
            await self.db.add_to_queue(song_request)

    async def testLeader(self):
        await self.reset_db()

        # create 3 users
        await self.db.get_user('user1')
        await self.db.get_user('user2')
        await self.db.get_user('user3')

        # add 1 rate to user1, 2 to user2, 3 to user3
        await self.add_rate('user1', 1)
        await self.add_rate('user2', 2)
        await self.add_rate('user3', 3)

        # check leader
        self.socket.from_twitch('!leader', self.channel, self.channel)
        await self.wrapper.read()
        expected = f'@{self.channel} Current leader is @user3 with 3 rates!'
        last = self.socket.get_last()
        self.assertEqual(last, expected)

    async def testStats(self):
        await self.reset_db()

        # create 3 users
        await self.db.get_user('user1')
        await self.db.get_user('user2')
        await self.db.get_user('user3')

        # add 1 rate to user1, 2 to user2, 3 to user3
        await self.add_rate('user1', 1)
        await self.add_rate('user2', 2)
        await self.add_rate('user3', 3)

        # add 3 song requests from user2
        await self.add_request('user2', 3)

        # check stats
        self.socket.from_twitch('!stats', 'user2', self.channel)
        await self.wrapper.read()
        expected = f'@user2 Your position is 2 with 2 rates from 3 requests and 0 rates given!'
        last = self.socket.get_last()
        self.assertEqual(last, expected)
