from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from twitch.wrapper import Wrapper, API


class Chatter:
    def __init__(self, tags: dict, api: 'API'):
        self.api = api
        self.tags: dict[str, str] = tags
        self.id: str = self.tags['user-id']
        self.name: str = self.tags['display-name']
        self.is_broadcaster: bool = self._is_broadcaster()
        self.username: str = self.name.lower()

    def _is_broadcaster(self):
        badges = self.tags['badges']
        return 'broadcaster' in badges

    async def is_subscriber(self):
        return self.tags.get('subscriber') == '1'

    async def is_mod(self):
        return self.tags.get('mod') == '1'

    async def is_follower(self) -> bool:
        return await self.api.is_follower(self.id)

    async def is_vip(self):
        return self.tags.get('vip') == '1'


class Message:
    def __init__(self, raw: str, service: 'Wrapper'):
        self.wrapper = service
        # split the '@tags' block off at the first space; tag values such as
        # `emotes` legitimately contain colons, so never split tags on ':'
        tag_str, _, rest = raw[1:].partition(' ') if raw.startswith('@') \
            else ('', '', raw)
        self.tags = self._get_tags(tag_str)
        self.id: str = self._get_id()
        self.chatter = self._get_chatter()
        self.content = self._get_message(rest)
        self.timestamp = self.tags['tmi-sent-ts']
        self.room_id = self.tags['room-id']

    def _get_id(self) -> str:
        return self.tags['id']

    def _get_chatter(self) -> Chatter:
        return Chatter(self.tags, self.wrapper.api)

    def _get_message(self, rest: str) -> str:
        # `rest` is ':source COMMAND params :trailing'; the body is everything
        # after the source prefix, so drop the first two ':'-separated parts
        content = rest.split(':')[2:]
        return ':'.join(content).strip('\r\n')

    def _get_tags(self, tag_str: str) -> dict:
        if not tag_str:
            return {}
        pairs = [tag.split('=', 1) for tag in tag_str.split(';')]
        return {pair[0]: pair[1] if len(pair) > 1 else '' for pair in pairs}

    async def reply(self, message: str):
        await self.wrapper.send(f"@{self.chatter.name} {message}")

    async def send(self, message: str):
        await self.wrapper.send(message)
