from prisma.models import User


class SongReq:
    def __init__(self, name: str, artist: str,
                 url: str, requester: str) -> None:
        self.name = name
        self.artist = artist
        self.url = url
        self.requester = requester

    def dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "artist": self.artist,
            "url": self.url,
            "requester": self.requester,
        }


class Leaderboard:
    def __init__(self, sorted: list[User]):
        self.sorted: list[User] = sorted

    @property
    def sorted_users(self) -> str:
        arr = [user.username for user in self.sorted]
        return '\n'.join(arr)

    @property
    def sorted_rates(self) -> str:
        arr = [str(user.rates) for user in self.sorted]
        return '\n'.join(arr)

    @property
    def sorted_position(self) -> str:
        arr = [str(i + 1) for i in range(len(self.sorted))]
        return '\n'.join(arr)
