import socket
import time
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from utils.creds import Creds


class MockSocket(socket.socket):
    def __init__(self, creds: 'Creds'):
        self.last_sent = b''
        self.creds = creds
        self._recv = ''

    def connect(self, host):
        self._recv = f':tmi.twitch.tv 001 {self.creds.twitch.channel} :Welcome, GLHF!'

    def close(self):
        pass

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
        msg = raw.split(':')[1].strip('\n')
        # replace on spaces bigger than 1 with a single space
        msg = ' '.join(msg.split())
        return msg
