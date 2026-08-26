import asyncio
from typing import Callable, Optional

# creates a timer that calls a function after given number of milliseconds


class Timer:
    def __init__(self, timeout: int, callback: Callable,
                 args: Optional[list] = None):
        # convert milliseconds to seconds
        self._timeout = float(timeout / 1000)
        self._callback = callback
        # mutable default arg shared across instances
        # so we use None and set it to an empty list in constructor
        self._args = args if args is not None else []
        self._task = asyncio.ensure_future(self._job())

    async def _job(self):
        await asyncio.sleep(self._timeout)
        await self._callback(*self._args)

    def cancel(self):
        self._task.cancel()
