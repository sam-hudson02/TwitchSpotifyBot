from discord import Webhook, WebhookMessage, Embed
from table2ascii import table2ascii as t2a, PresetStyle
from utils.db import DB, Leaderboard
from prisma.models import Queue as QueueModel
from utils.logger import Log
from typing import Optional
import asyncio
import aiohttp


class DiscordHook:
    def __init__(self, queue_url: str | None, leaderboard_url: str | None,
                 db: DB, channel: str, log: Log,
                 session: Optional[aiohttp.ClientSession] = None):
        self.log = log
        self.db = db
        self.twitch_channel = channel
        self.queue: list[QueueModel] = []
        self.leaderboard: Leaderboard = Leaderboard([])

        if session is None:
            self.session = aiohttp.ClientSession()
        else:
            self.session = session

        self.queue_webhook: Webhook | None = None
        if queue_url is not None:
            self.log.info('Creating webhook for queue')
            self.queue_webhook = Webhook.from_url(
                queue_url, session=self.session)

        self.leaderboard_webhook: Webhook | None = None
        if leaderboard_url is not None:
            self.log.info('Creating webhook for leaderboard')
            self.leaderboard_webhook = Webhook.from_url(
                leaderboard_url, session=self.session)

        self.q_message: WebhookMessage | None = None
        self.l_message: WebhookMessage | None = None

    def embed_queue(self, queue: list[QueueModel]):
        if len(queue) == 0:
            return f"{self.twitch_channel} Song Request Queue: \n" \
                   f"```\nQueue is Currently Empty!\n```"

        body = []
        header = ['Position', 'Track', 'Artist/s', 'Requester', 'id']
        for req in queue:
            body.append([req.position,
                         req.name,
                         req.artist,
                         req.requester,
                         req.id])

        queue_content = f"{self.twitch_channel} Song Request Queue: \n" \
                        f"```\n{t2a(header=header, body=body, style=PresetStyle.thin_rounded)}\n```"

        if len(queue_content) < 2000:
            return queue_content
        else:
            return 'Problem with queue :/'

    async def embed_leaderboard(self, leaderboard: Leaderboard):
        leaderboard = await self.db.get_leaderboard()
        embed = Embed(
            title=f'{self.twitch_channel}\'s Song Request Leaderboard')
        if len(leaderboard.sorted) > 0:
            embed.add_field(name='Position', value=leaderboard.sorted_position,
                            inline=True)
            embed.add_field(name='User', value=leaderboard.sorted_users,
                            inline=True)
            embed.add_field(name='Rates', value=leaderboard.sorted_rates,
                            inline=True)
        else:
            embed.add_field(name='Leaderboard is currently empty!',
                            value='No has received any rates yet!')
        return embed

    async def send_queue(self):
        # if self.message is None create a new message
        # else edit the message
        if self.queue_webhook is None:
            return

        q = self.embed_queue(self.queue)
        if self.q_message is None:
            self.log.info('Sending new queue message')
            self.q_message = await self.queue_webhook.send(content=q,
                                                           wait=True)
        else:
            self.log.info('Updating queue message')
            self.q_message = await self.q_message.edit(content=q)

    async def send_leaderboard(self):
        if self.leaderboard_webhook is None:
            return

        embeds = [await self.embed_leaderboard(self.leaderboard)]
        if self.l_message is None:
            self.log.info('Sending new leaderboard message')
            self.l_message = await self.leaderboard_webhook.send(embeds=embeds,
                                                                 wait=True)
        else:
            self.log.info('Updating leaderboard message')
            self.l_message = await self.l_message.edit(embeds=embeds)

    async def check_queue(self):
        new_queue = await self.db.get_queue()
        if new_queue != self.queue:
            self.queue = new_queue
            await self.send_queue()

    async def check_leaderboard(self):
        new_leaderboard = await self.db.get_leaderboard()
        if new_leaderboard.sorted != self.leaderboard.sorted:
            self.leaderboard = new_leaderboard
            await self.send_leaderboard()

    async def update(self):
        while True:
            await self.check_queue()
            await self.check_leaderboard()
            await asyncio.sleep(2)

    async def cleanup(self):
        if self.q_message is not None:
            await self.q_message.delete()
        if self.l_message is not None:
            await self.l_message.delete()
        # disconnect from discord
        if self.leaderboard_webhook is not None:
            await self.leaderboard_webhook.session.close()
        if self.queue_webhook is not None:
            await self.queue_webhook.session.close()

    def __del__(self):
        self.log.info('Cleaning up discord hook')
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(self.cleanup())
