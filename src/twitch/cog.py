from typing import TYPE_CHECKING

from twitch.message import Message
if TYPE_CHECKING:
    from twitch.bot import Bot
    from twitch.router import Context


class Cog:
    def __init__(self, bot: 'Bot'):
        self.bot = bot

    async def before_invoke(self, ctx: 'Context') -> bool:
        return True

    async def after_invoke(self, ctx: 'Context') -> None:
        pass

    async def load(self) -> None:
        pass

    async def on_error(self, msg: Message, error: Exception) -> None:
        raise error
