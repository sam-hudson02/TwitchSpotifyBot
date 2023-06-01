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
        if self.tags['subscriber'] == '1':
            return True
        return False

    async def is_mod(self):
        if self.tags['mod'] == '1':
            return True
        return False

    async def is_follower(self) -> bool:
        # TODO: make this work
        return await self.api.is_follower(self.id)

    async def is_vip(self):
        if self.tags['vip'] == '1':
            return True
        return False


class Message:
    def __init__(self, raw: str, service: 'Wrapper'):
        self.wrapper = service
        self.tags = self._get_tags(raw)
        self.id: str = self._get_id()
        self.chatter = self._get_chatter()
        self.content = self._get_message(raw)
        self.timestamp = self.tags['tmi-sent-ts']
        self.room_id = self.tags['room-id']

    def _get_id(self) -> str:
        return self.tags['id']

    def _get_chatter(self) -> Chatter:
        return Chatter(self.tags, self.wrapper.api)

    def _get_message(self, raw: str) -> str:
        content = raw.split(':')[2:]
        return ':'.join(content).strip('\r\n')

    def _get_tags(self, raw: str) -> dict:
        tags = raw.split(':')[0]
        tags = tags.split(';')
        tags = [tag.split('=') for tag in tags]
        if tags == [['']]:
            return {}
        return {tag[0]: tag[1] for tag in tags}

    async def reply(self, message: str):
        await self.wrapper.send(f"@{self.chatter.name} {message}")
