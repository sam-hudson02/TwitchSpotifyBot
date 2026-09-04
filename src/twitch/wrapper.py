import asyncio
from utils.creds import TwitchCreds
from utils.twitch_token import TwitchToken
from typing import Awaitable, Callable, Optional
import socket
import random
from twitch.message import Message
import threading as th
from utils.logger import Log
import aiohttp


class Wrapper:
    def __init__(self, creds: TwitchCreds,
                 sock: Optional[socket.socket] = None,
                 token: Optional[TwitchToken] = None,
                 read_sock: Optional[socket.socket] = None):
        self.token = token or TwitchToken(creds)
        self.api = API(creds, self.token)
        self.log = Log('Socket')
        self.creds = creds
        self._on_message: Callable[[Message], Awaitable[None]] = self.empty
        self._on_live: Callable[[None], Awaitable[None]] = self.empty
        self._on_offline: Callable[[None], Awaitable[None]] = self.empty
        self.server = 'irc.chat.twitch.tv'
        self.port = 6667
        # authenticated connection, used to send messages as the bot account
        self.send_sock: Optional[socket.socket] = sock
        # anonymous connection, used to read chat. Twitch does not echo a
        # user's own messages back to their authenticated session, so an
        # anonymous reader is needed to see messages from the bot's own account.
        self.read_sock: Optional[socket.socket] = read_sock or sock
        self._listen_task: Optional[asyncio.Task] = None

    async def empty(self, *args, **kwargs):
        pass

    async def connect(self, tries: int = 0):
        try:
            token = await self.token.get()
            if self.send_sock is None:
                self.send_sock = socket.socket()
            if self.read_sock is None:
                self.read_sock = socket.socket()
            self.log.info(f"Connecting to {self.server}:{self.port}")

            # authenticated connection: sends messages as the bot account
            self.send_sock.connect((self.server, self.port))
            self.send_sock.send('CAP REQ :twitch.tv/membership twitch.tv/tags\n'
                                .encode("utf-8"))
            self.send_sock.send(f"PASS oauth:{token}\n".encode("utf-8"))
            self.send_sock.send(f"NICK {self.creds.bot_name}\n".encode("utf-8"))
            self.send_sock.send(f"JOIN #{self.creds.channel}\n".encode("utf-8"))
            resp = self.send_sock.recv(2048).decode("utf-8")
            if 'Login authentication failed' in resp:
                # token was rejected: refresh it and let the retry loop reconnect
                self.log.error('Twitch rejected the access token, refreshing')
                await self.token.get(force=True)
                raise ConnectionError('Login authentication failed')

            # anonymous connection: reads all chat, including messages sent from
            # the bot's own account (which Twitch will not echo to send_sock)
            anon_nick = f"justinfan{random.randint(10000, 99999)}"
            self.read_sock.connect((self.server, self.port))
            self.read_sock.send('CAP REQ :twitch.tv/membership twitch.tv/tags\n'
                                .encode("utf-8"))
            self.read_sock.send(f"NICK {anon_nick}\n".encode("utf-8"))
            self.read_sock.send(f"JOIN #{self.creds.channel}\n".encode("utf-8"))
            self.read_sock.recv(2048)

            self.log.info('Socket connected')
            await self._on_join(self.creds.channel)
        except Exception as err:
            self._close_sockets()
            self.log.error(f"Error connecting to socket: {err}")
            await asyncio.sleep(1.5 ** tries)
            if tries < 5:
                self.log.info(f"Retrying connection {tries + 1}/5")
                await self.connect(tries + 1)
            else:
                self.log.critical('Max retries reached, giving up on the \
                                  Twitch connection')
                raise ConnectionError('Could not connect to Twitch IRC')

    def _close_sockets(self):
        for name in ('send_sock', 'read_sock'):
            sock = getattr(self, name)
            if sock is None:
                continue
            try:
                sock.close()
            except Exception as e:
                self.log.error(f'Error closing socket: {e}')
            setattr(self, name, None)

    def disconnect(self):
        if self.send_sock is not None:
            self.log.info('Disconnecting socket')
            try:
                self.send_sock.send(
                    f"PART #{self.creds.channel}\n".encode("utf-8"))
            except Exception as e:
                self.log.error(f'Error sending PART: {e}')
        self._close_sockets()

    async def cleanup(self):
        if self._listen_task is not None:
            self._listen_task.cancel()
            self._listen_task = None
        self.disconnect()
        await self.api.close()

    async def start(self):
        await self.connect()
        # listen on the running loop so message handling (DB, token, HTTP) stays
        # on the same loop everything else is bound to; only the blocking socket
        # recv is offloaded (see read()).
        self._listen_task = asyncio.create_task(self.listen())
        # keep the authenticated (send) connection alive by answering its PINGs
        th.Thread(target=self._keepalive_loop, daemon=True).start()

    def _keepalive_loop(self):
        # the send connection never routes messages (they arrive on read_sock),
        # but it must still respond to Twitch PINGs or it will be dropped
        while True:
            try:
                if self.send_sock is None:
                    return
                resp = self.send_sock.recv(2048).decode("utf-8")
                if resp.startswith("PING"):
                    self.send_sock.send("PONG\n".encode("utf-8"))
            except Exception as e:
                self.log.error(f'Send socket error: {e}')
                return

    async def send(self, message: str):
        if self.send_sock is None:
            return
        self.send_sock.send(f"PRIVMSG #{self.creds.channel} :{message}\n"
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
        return resp.startswith("@") and " PRIVMSG " in resp

    async def read(self):
        if self.read_sock is None:
            return
        # recv blocks, so run it in a worker thread; the handlers it feeds then
        # run back on the event loop (where the DB/token/HTTP clients live)
        raw = await asyncio.to_thread(self.read_sock.recv, 2048)
        data = raw.decode("utf-8")
        for line in data.split("\r\n"):
            await self._handle_line(line)

    async def _handle_line(self, line: str):
        if not line:
            return
        if line.startswith("PING"):
            if self.read_sock is not None:
                self.read_sock.send("PONG\n".encode("utf-8"))
            return
        if not self.is_message(line):
            return
        try:
            msg = Message(line, self)
        except Exception as e:
            self.log.error(f'Could not parse message: {e}')
            return
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
        channel_id = await self.channel_id()
        params = {'broadcaster_id': channel_id, 'user_id': user_id}
        # needs the moderator:read:followers scope and the bot to be a
        # moderator of the channel
        resp = await self.do_call('channels/followers', params)
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
