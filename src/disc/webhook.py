import asyncio
from discord import Webhook, WebhookMessage, Embed
from table2ascii import table2ascii as t2a, PresetStyle
import aiohttp
from utils.db import DB, Leaderboard
from prisma.models import Queue as QueueModel

from utils.logger import Log


class DiscordHook:
    def __init__(self, queue_url: str | None, leaderboard_url: str | None,
                 db: DB, channel: str, log: Log):
        self.log = log
        self.db = db
        self.twitch_channel = channel
        self.queue: list[QueueModel] = []
        self.leaderboard: Leaderboard = Leaderboard([])

        self.queue_webhook: Webhook | None = None
        if queue_url is not None:
            session = aiohttp.ClientSession()
            self.queue_webhook = Webhook.from_url(
                queue_url, session=session)

        self.leaderboard_webhook: Webhook | None = None
        if leaderboard_url is not None:
            session = aiohttp.ClientSession()
            self.leaderboard_webhook = Webhook.from_url(
                leaderboard_url, session=session)

        self.q_message: WebhookMessage | None = None
        self.l_message: WebhookMessage | None = None

    def embed_queue(self):
        if len(self.queue) == 0:
            return f"{self.twitch_channel} Song Request Queue: \n" \
                   f"```\nQueue is Currently Empty!\n```"

        body = []
        header = ['Position', 'Track', 'Artist/s', 'Requester', 'id']
        for req in self.queue:
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

    def search_queue_message(self):
        # search the queue message in the channel
        # if it exists return it 

        if self.queue_webhook is None:
            return

        messages = self.queue_webhook.channel.messages

    async def embed_leaderboard(self):
        leaderboard = await self.db.get_leaderboard()
        embed = Embed(
            title=f'{self.twitch_channel} Song Request Leaderboard')
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

        q = self.embed_queue()
        if self.q_message is None:
            self.q_message = await self.queue_webhook.send(content=q,
                                                           wait=True)
        else:
            self.q_message = await self.q_message.edit(content=q)

    async def send_leaderboard(self):
        if self.leaderboard_webhook is None:
            return

        embeds = [await self.embed_leaderboard()]
        if self.l_message is None:
            self.l_message = await self.leaderboard_webhook.send(embeds=embeds,
                                                                 wait=True)
        else:
            self.l_message = await self.l_message.edit(embeds=embeds)

    async def check_queue(self):
        new_queue = await self.db.get_queue()
        if new_queue != self.queue:
            self.log.info('Queue has changed')
            self.queue = new_queue
            await self.send_queue()
        else:
            self.log.info('Queue is the same')

    async def check_leaderboard(self):
        new_leaderboard = await self.db.get_leaderboard()
        if new_leaderboard.sorted != self.leaderboard.sorted:
            self.log.info('Leaderboard has changed')
            self.leaderboard = new_leaderboard
            await self.send_leaderboard()
        else:
            self.log.info('Leaderboard is the same')

    async def update(self):
        while True:
            print('Checking for updates')
            await self.check_queue()
            await self.check_leaderboard()
            await asyncio.sleep(2)
