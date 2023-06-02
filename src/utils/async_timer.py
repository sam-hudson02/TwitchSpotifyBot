import asyncio

# creates a timer that calls a function after given number of milliseconds


class Timer:
    def __init__(self, timeout: int, callback: callable, args: list = []):
        # convert milliseconds to seconds
        self._timeout = float(timeout / 1000)
        self._callback = callback
        self._task = asyncio.ensure_future(self._job())
        self._args = args

    async def _job(self):
        await asyncio.sleep(self._timeout)
        await self._callback(*self._args)

    def cancel(self):
        self._task.cancel()
