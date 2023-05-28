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
