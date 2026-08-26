class SongReqError(Exception):
    def __str__(self):
        return self.__class__.__name__


class YoutubeLink(SongReqError):
    pass


class BadPerms(SongReqError):
    def __init__(self, perm: str):
        self.perm = perm


class UnsupportedLink(SongReqError):
    pass


class NotActive(SongReqError):
    pass


class UserBanned(SongReqError):
    pass


class TrackNotFound(SongReqError):
    pass


class TrackAlreadyInQueue(SongReqError):
    def __init__(self, track: str, artist: str):
        self.track = track
        self.artist = artist


class PlaybackError(Exception):
    def __str__(self):
        return self.__class__.__name__


class NoCurrentTrack(PlaybackError):
    pass


class UtilError(Exception):
    def __init__(self, message: str):
        self.message = message


class TargetNotFound(UtilError):
    pass


class TimeNotFound(UtilError):
    pass


class TrackRecentlyPlayed(Exception):
    def __init__(self, track: str, artist: str):
        self.track = track
        self.artist = artist


class NotAuthorized(Exception):
    def __init__(self, clearance_required: str):
        self.clearance = clearance_required


class SetupError(Exception):
    def __str__(self):
        return self.__class__.__name__
    pass


class NoCreds(SetupError):
    def __init__(self, missing: str):
        print(f'No {missing} credential found.')
    pass


class SettingsError(SetupError):
    def __init__(self, message: str):
        self.message = message


class BadLink(Exception):
    def __str__(self):
        return self.__class__.__name__
    pass
