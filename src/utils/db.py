from prisma import Prisma
from prisma.models import User, Queue
from utils.types import SongReq
from utils.errors import TrackAlreadyInQueue


class Leaderboard:
    def __init__(self, sorted: list[User]):
        self.sorted = sorted

    @property
    def sorted_users(self) -> list[str]:
        return [user.username for user in self.sorted]

    @property
    def sorted_rates(self) -> list[int]:
        return [user.rates for user in self.sorted]

    @property
    def sorted_position(self) -> list[int]:
        return [i + 1 for i in range(len(self.sorted))]


class DB:
    def __init__(self):
        self.client = Prisma()

    async def connect(self):
        await self.client.connect()

    async def reset_all_user_stats(self) -> None:
        await self.client.user.update_many(
            where={},
            data={
                "requests": 0,
                "rates": 0,
                "ratesGiven": 0,
            },
        )

    async def get_user(self, username) -> User:
        user = await self.client.user.find_unique(where={"username": username})
        if user is None:
            user = await self.client.user.create(data={"username": username})
        return user

    async def get_user_position(self, username,
                                user: User | None = None) -> int:
        if user is None:
            user = await self.get_user(username)
        return await self.client.user.count(
            where={"rates": {"gt": user.rates}}
        ) + 1

    async def add_rate(self, receiver: str, giver: str) -> None:
        receiver_user = await self.get_user(receiver)
        giver_user = await self.get_user(giver)
        await self.client.user.update(
            where={"username": receiver},
            data={
                "rates": receiver_user.rates + 1,
            },
        )
        await self.client.user.update(
            where={"username": giver},
            data={
                "ratesGiven": giver_user.ratesGiven + 1,
            },
        )

    async def get_leader(self) -> User | None:
        return await self.client.user.find_first(
            where={},
            order={"rates": "desc"},
        )

    async def get_leaderboard(self) -> Leaderboard:
        users = await self.client.user.find_many(
            where={},
            order={"rates": "desc"},
        )
        return Leaderboard(users)

    async def get_all_users(self) -> list[User]:
        return await self.client.user.find_many(where={})

    async def get_next_song(self) -> Queue | None:
        return await self.client.queue.find_first(
            where={},
            order={"position": "desc"},
        )

    async def check_if_in_queue(self, song: SongReq) -> bool:
        return await self.client.queue.find_first(
            where={
                'name': song.name,
                'artist': song.artist,
            },
        ) is not None

    async def add_to_queue(self, song: SongReq) -> None:
        if await self.check_if_in_queue(song):
            raise TrackAlreadyInQueue(track=song.name, artist=song.artist)

        position = await self.client.queue.count(where={}) + 1
        await self.client.queue.create(
            data={
                "name": song.name,
                "artist": song.artist,
                "url": song.url,
                "requester": song.requester,
                "position": position,
            }
        )

        await self.client.user.upsert(
            where={"username": song.requester},
            data={
                'create': {
                    "username": song.requester,
                },
                'update': {
                    "requests": {
                        "increment": 1,
                    },
                },
            },
        )

    async def get_queue(self) -> list[Queue]:
        return await self.client.queue.find_many(
            where={},
            order={"position": "desc"},
        )

    async def clear_queue(self) -> None:
        await self.client.queue.delete_many(where={})

    async def remove_from_queue(self, req_id: int) -> None:
        await self.client.queue.delete(
            where={
                'id': req_id,
            },
        )

    async def get_requester(self, url: str) -> str:
        song = await self.client.queue.find_first(where={"url": url})
        if song is None:
            return ""
        return song.requester

    async def ban_user(self, username: str) -> None:
        await self.client.user.update(
            where={"username": username},
            data={
                "ban": True,
            },
        )

    async def unban_user(self, username: str) -> None:
        await self.client.user.update(
            where={"username": username},
            data={
                "ban": False,
            },
        )

    async def delete_all(self) -> None:
        await self.client.user.delete_many(where={})
        await self.client.queue.delete_many(where={})

    async def mod_user(self, username: str) -> None:
        await self.client.user.upsert(
            where={"username": username},
            data={
                'create': {
                    "username": username,
                    "mod": True,
                },
                'update': {
                    "mod": True,
                }
            },
        )

    async def admin_user(self, username: str) -> None:
        await self.client.user.upsert(
            where={"username": username},
            data={
                'create': {
                    "username": username,
                    "admin": True,
                    "mod": True,
                },
                'update': {
                    "admin": True,
                    "mod": True,
                }
            },
        )

    async def unmod_user(self, username: str) -> None:
        await self.client.user.update(
            where={"username": username},
            data={
                "mod": False,
            },
        )
