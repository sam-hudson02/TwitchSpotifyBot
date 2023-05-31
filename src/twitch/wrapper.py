import asyncio
from utils.creds import TwitchCreds
from typing import Awaitable, Callable, Optional
import socket
from twitch.message import Message
import threading as th
from utils.logger import Log


class Wrapper:
    def __init__(self, creds: TwitchCreds, sock: Optional[socket.socket] = None):
        self.log = Log('Socket')
        self.creds = creds
        self._on_message: Callable[[Message], Awaitable[None]] = self.empty
        self._on_live: Callable[[None], Awaitable[None]] = self.empty
        self._on_offline: Callable[[None], Awaitable[None]] = self.empty
        self.server = 'irc.chat.twitch.tv'
        self.port = 6667
        self.sock: Optional[socket.socket] = sock

    async def empty(self, *args, **kwargs):
        pass

    async def connect(self, tries: int = 0):
        try:
            if self.sock is None:
                self.sock = socket.socket()
            self.log.info(f"Connecting to {self.server}:{self.port}")
            self.sock.connect((self.server, self.port))
            self.sock.send('CAP REQ :twitch.tv/membership twitch.tv/tags\n'
                           .encode("utf-8"))
            self.sock.send(f"PASS oauth:{self.creds.token}\n".encode("utf-8"))
            self.sock.send(f"NICK {self.creds.bot_name}\n".encode("utf-8"))
            self.sock.send(f"JOIN #{self.creds.channel}\n".encode("utf-8"))
            self.sock.recv(2048).decode("utf-8")
            self.log.info('Socket connected')
            await self._on_join(self.creds.channel)
        except Exception as e:
            try:
                self.sock.close()
                self.sock = None
            except Exception as e:
                self.log.error(f'Error closing socket: {e}')
            self.log.error(f"Error connecting to socket: {e}")
            await asyncio.sleep(1.5 ** tries)
            if tries < 5:
                self.log.info(f"Retrying connection {tries + 1}/5")
                await self.connect(tries + 1)
            else:
                self.log.error('Max retries reached')
                # exit entire program
                exit(1)

    def disconnect(self):
        if self.sock is None:
            return
        self.log.info('Disconnecting socket')
        self.sock.send(f"PART #{self.creds.channel}\n".encode("utf-8"))
        self.sock.close()

    async def start(self):
        await self.connect()
        th.Thread(target=self.run_listen).start()

    def run_listen(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.create_task(self.listen())
        loop.run_forever()

    async def send(self, message: str):
        if self.sock is None:
            return
        self.sock.send(f"PRIVMSG #{self.creds.channel} :{message}\n"
                       .encode("utf-8"))

    def on_join(self, func: Callable[[str], Awaitable[None]]):
        self._on_join = func

    def on_message(self, func: Callable[[Message], Awaitable[None]]):
        self._on_message = func

    def on_live(self, func: Callable[[None], Awaitable[None]]):
        self._on_live = func

    def on_offline(self, func: Callable[[None], Awaitable[None]]):
        self._on_offline = func

    def is_message(self, resp: str) -> bool:
        return resp.startswith("@")

    async def read(self):
        if self.sock is None:
            return
        resp = self.sock.recv(2048).decode("utf-8")
        if resp.startswith("PING"):
            self.sock.send("PONG\n".encode("utf-8"))
        elif len(resp) > 0 and self.is_message(resp):
            msg = Message(resp, self)
            await self._on_message(msg)

    async def listen(self):
        self.log.info('Listening to socket')
        while True:
            await self.read()
