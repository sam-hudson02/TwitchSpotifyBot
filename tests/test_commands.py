import asyncio
import sys
import unittest
import socket
import time
import threading as th
sys.path.append('src')
sys.path.append('tests')
if True:
    from utils.settings import Settings
    from utils.logger import Log
    from utils.db import DB
    from utils.creds import Creds
    from twitch.wrapper import Wrapper
    from twitch.bot import Bot
    from AudioController.spotify_api import Spotify
    from AudioController.audio_controller import AudioController, Context
# add src to path


class MockSocket(socket.socket):
    def __init__(self, creds: Creds):
        self.last_sent = b''
        self.creds = creds
        self._recv = ''

    def connect(self, host):
        self._recv = f':tmi.twitch.tv 001 {self.creds.twitch.channel} :Welcome, GLHF!'

    def send(self, data):
        self.last_sent = data

    def recv(self, size):
        while self._recv == '':
            time.sleep(0.1)
        response = self._recv
        self._recv = ''
        return response.encode('utf-8')

    def from_twitch(self, msg, author, channel, badges='something/something', sub=False):
        self._recv = f"@badge-info=;badges={badges},premium/1;client-nonce=2236c00d2eee968a40646ac7b169ed81;color=;display-name={channel};emotes=;first-msg=0;flags=;id=ea69b4b1-a28c-4321-8812-cea9bc5c8d62;mod=0;returning-chatter=0;room-id=151470592;subscriber={int(sub)};tmi-sent-ts=1685411550601;turbo=0;user-id=151470592;user-type= :samtheno0b!samtheno0b@samtheno0b.tmi.twitch.tv PRIVMSG #samtheno0b :{msg}"

    def get_last(self):
        raw = self.last_sent.decode('utf-8')
        return raw.split(':')[1].strip('\n')


class TestCommands(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.creds = Creds()
        self.socket = MockSocket(self.creds)
        self.wrapper = Wrapper(self.creds.twitch, self.socket)
        self.db = DB()
        await self.db.connect()
        self.spot = Spotify(self.creds.spotify)
        self.audio_ctx = Context()
        log = Log('AC')
        self.ac = AudioController(self.db, self.spot, self.audio_ctx, log)
        self.settings = Settings()
        self.bot = Bot(self.wrapper,  self.db, self.settings,
                       self.ac, self.creds.twitch)
        await self.bot.load_cogs()
        print('setup complete')
        self.channel = self.creds.twitch.channel
        self.author = self.creds.twitch.channel

    async def test_song(self):
        self.socket.from_twitch('!song', self.channel, self.channel)
        await self.ac.update_context()
        await self.wrapper.read()
        self.assertIsNotNone(self.socket.get_last())
        print(self.socket.get_last())
