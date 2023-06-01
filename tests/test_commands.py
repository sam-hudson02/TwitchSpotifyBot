import unittest
from utils.settings import Settings
from utils.logger import Log
from utils.db import DB
from utils.creds import Creds
from twitch.wrapper import Wrapper
from twitch.bot import Bot
from AudioController.audio_controller import AudioController, Context
from mocks.mock_sock import MockSocket
from mocks.mock_spot import MockSpot
# add src to path


class TestCommands(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.creds = Creds()
        self.socket = MockSocket(self.creds)
        self.wrapper = Wrapper(self.creds.twitch, self.socket)
        self.db = DB()
        await self.db.connect()
        await self.db.delete_all()
        self.channel = self.creds.twitch.channel
        await self.db.get_user(self.channel, True, True)
        self.spot = MockSpot()
        self.audio_ctx = Context()
        log = Log('AC')
        self.ac = AudioController(self.db, self.spot, self.audio_ctx, log)
        self.settings = Settings()
        self.bot = Bot(self.wrapper,  self.db, self.settings,
                       self.ac, self.creds.twitch)
        await self.bot.load_cogs()
        print('setup complete')

    async def testDev(self):
        self.socket.from_twitch('!dev-on', self.channel, self.channel)
        await self.wrapper.read()
        expected = f'@{self.channel} Dev mode has been turned on!'
        self.assertEqual(self.socket.get_last(), expected)
        self.socket.from_twitch('!dev-off', self.channel, self.channel)
        await self.wrapper.read()
        expected = f'@{self.channel} Dev mode has been turned off!'
        self.assertEqual(self.socket.get_last(), expected)

    async def testSr(self):
        self.socket.from_twitch('!dev-on', self.channel, self.channel)

        # add song 'test' to the queue
        self.socket.from_twitch('!sr test', self.channel, self.channel)
        await self.wrapper.read()
        expected = f'@{self.channel} test by test has been added to the queue!'
        self.assertEqual(self.socket.get_last(), expected)

        # check its in the db
        next = await self.db.get_next_song()
        if next is None:
            self.fail('song not in db')
        self.assertEqual(next.name, 'test')
        self.assertEqual(next.requester, self.channel)

        # shouldn't be able to add the same song twice
        self.socket.from_twitch('!sr test', self.channel, self.channel)
        await self.wrapper.read()
        expected = f'@{self.channel} That song is already in the queue!'
        self.assertEqual(self.socket.get_last(), expected)

        # add 'test2' to the queue using url from new account
        author = 'someuser'
        self.socket.from_twitch('!sr https://open.spotify.com/track/test2',
                                author, self.channel)
        await self.wrapper.read()
        expected = f'@{self.channel} test2 by test2 has been added to the queue!'
        self.assertEqual(self.socket.get_last(), expected)

    async def reqSong(self, request, name, artist):
        self.socket.from_twitch(f'!sr {request}', self.channel, self.channel)
        await self.wrapper.read()
        expected = f'@{self.channel} {name} by {artist} has been added to the queue!'
        self.assertEqual(self.socket.get_last(), expected)

        # check its in the db
        next = await self.db.get_next_song()
        if next is None:
            self.fail('song not in db')
        self.assertEqual(next.name, 'test')
        self.assertEqual(next.requester, self.channel)

    async def dbRefresh(self):
        await self.db.delete_all()
        await self.db.get_user(self.channel, True, True)

    async def testVeto(self):
        await self.dbRefresh()
        self.socket.from_twitch('!dev-on', self.channel, self.channel)

        # add song 'test' to the queue
        await self.reqSong('test', 'test', 'test')

        # veto the song
        author = 'someuser'
        self.socket.from_twitch('!veto', author, self.channel)
        await self.wrapper.read()
        expected = f'@{self.channel} 1 out of 5 chatters have voted to skip the current song!'
        self.assertEqual(self.socket.get_last(), expected)
