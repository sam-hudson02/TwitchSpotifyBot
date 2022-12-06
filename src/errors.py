class TargetNotFound(Exception):
    pass


class TimeNotFound(Exception):
    pass


class NotActive(Exception):
    pass


class UserBanned(Exception):
    pass


class TrackAlreadyInQueue(Exception):
    def __init__(self, track: str, artist: str):
        self.track = track
        self.artist = artist


class TrackRecentlyPlayed(Exception):
    def __init__(self, track: str, artist: str):
        self.track = track
        self.artist = artist


class NotAuthorized(Exception):
    def __init__(self, clearance_required: str):
        self.clearance = clearance_required


class UserAlreadyRole(Exception):
    def __init__(self, target: str, role: str, has_role: bool):
        self.target = target
        self.role = role
        self.has_role = has_role


class TrackNotFound(Exception):
    pass


class NoCreds(Exception):
    pass


class YoutubeLink(Exception):
    pass


class UnsupportedLink(Exception):
    pass


class DBError(Exception):
    pass


class NoCurrentTrack(Exception):
    pass
