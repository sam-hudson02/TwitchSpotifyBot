from prisma.models import User
from twitch.wrapper import Message
from typing import Callable, Awaitable, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from twitch.cog import Cog
    from twitch.bot import Bot


class Context:
    def __init__(self, user: User, command: str, msg: Message):
        self.user: User = user
        self.command: str = command
        self.msg: Message = msg
        self.chatter = msg.chatter
        self.content = self._get_content()

    async def reply(self, msg: str):
        print('replying')
        await self.msg.reply(msg)

    def _get_content(self):
        return self.msg.content[len(self.command) + 1:].strip()


class Command:
    def __init__(self, cog: Optional['Cog'], command: str,
                 func: Callable[[Context], Awaitable[None]]):
        self.command: str = command
        self.func: Callable[[Context], Awaitable[None]] = func
        self.cog: Optional['Cog'] = cog


class Router:
    def __init__(self, bot: 'Bot'):
        self.routes: dict[str, Command] = {}
        self.bot: 'Bot' = bot

    async def handle(self, msg: Message, command: str):
        print('handling ' + command)
        command_obj = self.routes.get(command, None)

        if command_obj is None:
            print('command not found')
            print(self.routes.keys())
            return

        if command_obj.cog is not None:
            await self.run_cog_command(command_obj.func, command_obj.cog, msg,
                                       command)
        else:
            await self.run_command(command_obj.func, msg, command)

    async def run_cog_command(self, func: Callable[[Context], Awaitable[None]],
                              cog: 'Cog', msg: Message, command: str):
        print('running cog command')
        try:
            user = await self.bot.db.get_user(msg.chatter.username)
            ctx = Context(user, command, msg)
            if not await cog.before_invoke(ctx):
                return
            await func(ctx)
            await cog.after_invoke(ctx)
        except Exception as e:
            await cog.on_error(msg, e)

    async def run_command(self, func: Callable[[Context], Awaitable[None]],
                          msg: Message, command: str):
        print('running command')
        try:
            user = await self.bot.db.get_user(msg.chatter.username)
            ctx = Context(user, command, msg)
            await func(ctx)
        except Exception as e:
            raise e

    def add_route(self, command: str,
                  func: Callable[[Context], Awaitable[None]],
                  cog: Optional['Cog'] = None):
        self.routes[command] = Command(cog, command, func)

    def remove_route(self, command: str):
        if command in self.routes:
            del self.routes[command]