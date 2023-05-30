import asyncio
from utils.creds import TwitchCreds
from typing import Awaitable, Callable, Optional
import socket
from twitch.message import Message
import threading as th


class Wrapper:
    def __init__(self, creds: TwitchCreds):
        self.creds = creds
        self._on_message: Callable[[Message], Awaitable[None]] = self.empty
        self._on_live: Callable[[None], Awaitable[None]] = self.empty
        self._on_offline: Callable[[None], Awaitable[None]] = self.empty
        self.server = 'irc.chat.twitch.tv'
        self.port = 6667
        self.sock: socket.socket | None = None

    async def empty(self, *args, **kwargs):
        print("empty")
        pass

    async def connect(self, sock: Optional[socket.socket] = None):
        if sock is not None:
            self.sock = sock
        else:
            self.sock = socket.socket()
        self.sock.connect((self.server, self.port))
        self.sock.send('CAP REQ :twitch.tv/membership twitch.tv/tags\n'
                       .encode("utf-8"))
        self.sock.send(f"PASS oauth:{self.creds.token}\n".encode("utf-8"))
        self.sock.send(f"NICK {self.creds.bot_name}\n".encode("utf-8"))
        self.sock.send(f"JOIN #{self.creds.channel}\n".encode("utf-8"))
        resp = self.sock.recv(2048).decode("utf-8")
        print(resp)
        await self._on_join(self.creds.channel)

    async def start(self):
        await self.connect()
        th.Thread(target=self.run_listen).start()

    def run_listen(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.listen())

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

    async def listen(self):
        while True:
            if self.sock is None:
                print("no socket")
                return
            resp = self.sock.recv(2048).decode("utf-8")
            print(resp)
            if resp.startswith("PING"):
                self.sock.send("PONG\n".encode("utf-8"))
            elif len(resp) > 0 and self.is_message(resp):
                msg = Message(resp, self)
                await self._on_message(msg)
