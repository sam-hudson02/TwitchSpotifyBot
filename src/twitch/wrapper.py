import asyncio
from utils.creds import TwitchCreds
from utils.twitch_token import TwitchToken
from typing import Awaitable, Callable, Optional
import socket
from twitch.message import Message
import threading as th
from utils.logger import Log
import aiohttp


class Wrapper:
    def __init__(self, creds: TwitchCreds,
                 sock: Optional[socket.socket] = None,
                 token: Optional[TwitchToken] = None):
        self.token = token or TwitchToken(creds)
        self.api = API(creds, self.token)
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
            token = await self.token.get()
            self.sock.connect((self.server, self.port))
            self.sock.send('CAP REQ :twitch.tv/membership twitch.tv/tags\n'
                           .encode("utf-8"))
            self.sock.send(f"PASS oauth:{token}\n".encode("utf-8"))
            self.sock.send(f"NICK {self.creds.bot_name}\n".encode("utf-8"))
            self.sock.send(f"JOIN #{self.creds.channel}\n".encode("utf-8"))
            resp = self.sock.recv(2048).decode("utf-8")
            if 'Login authentication failed' in resp:
                # token was rejected: refresh it and let the retry loop reconnect
                self.log.error('Twitch rejected the access token, refreshing')
                await self.token.get(force=True)
                raise ConnectionError('Login authentication failed')
            self.log.info('Socket connected')
            await self._on_join(self.creds.channel)
        except Exception as err:
            try:
                if self.sock is not None:
                    self.sock.close()
                self.sock = None
            except Exception as e:
                self.log.error(f'Error closing socket: {e}')
            self.log.error(f"Error connecting to socket: {err}")
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

    async def cleanup(self):
        self.disconnect()
        await self.api.close()

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


class API:
    def __init__(self, creds: TwitchCreds, token: TwitchToken) -> None:
        self.creds = creds
        self.token = token
        self.log = Log('API')
        self.base_url: str = 'https://api.twitch.tv/helix/'
        self.session = aiohttp.ClientSession()
        self.channel: str = creds.channel
        self._channel_id: Optional[str] = None

    async def do_call(self, endpoint: str, params: Optional[dict] = None,
                      headers: Optional[dict] = None,
                      base_url: Optional[str] = None,
                      retried: bool = False):
        try:
            if base_url is None:
                base_url = self.base_url
            url = base_url + endpoint
            if params is None:
                params = {}
            if headers is None:
                headers = await self.headers()
            resp = await self.session.get(url, headers=headers,
                                          params=params)
            if resp.status == 401 and not retried:
                # the access token was rejected: refresh and retry once
                self.log.info('Helix returned 401, refreshing access token')
                await self.token.get(force=True)
                return await self.do_call(endpoint, params=params,
                                          base_url=base_url, retried=True)
            if resp.status != 200:
                err = await resp.json()
                self.log.error(f'Error calling {endpoint}: {err["message"]}')
                return None
            return await resp.json()
        except Exception as err:
            self.log.error(f'Error calling {endpoint}: {err}')
            return None

    async def is_follower(self, user_id: str) -> bool:
        params = {'from_id': user_id, 'to_id': self.channel_id}
        resp = await self.do_call('users/follows', params)
        if resp is None:
            return False
        return len(resp['data']) > 0

    async def is_live(self) -> bool:
        channel_id = await self.channel_id()
        params = {'user_id': channel_id}
        resp = await self.do_call('streams', params)
        if resp is None:
            return False
        return len(resp['data']) > 0

    async def get_channel_id(self, channel_name: str) -> Optional[str]:
        params = {'login': channel_name}
        resp = await self.do_call('users', params)
        if resp is None:
            return None
        return resp['data'][0]['id']

    async def channel_id(self) -> str:
        if self._channel_id is None:
            self._channel_id = await self.get_channel_id(self.channel)
            if self._channel_id is None:
                raise Exception('Could not get channel id')
        return self._channel_id

    async def headers(self) -> dict[str, str]:
        token = await self.token.get()
        return {
            'Authorization': f'Bearer {token}',
            'Client-Id': self.creds.client_id,
        }

    async def close(self):
        await self.session.close()
