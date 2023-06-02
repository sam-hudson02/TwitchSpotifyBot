from dotenv import load_dotenv
from utils.errors import NoCreds
from utils.logger import Log
from os import getenv


def get_str_env(name: str) -> str:
    value = getenv(name)
    if value is None:
        raise NoCreds(name)
    return value


def get_int_env(name: str) -> int:
    value = getenv(name)
    if value is None:
        raise NoCreds(name)
    return int(value)


def get_bool_env(name: str) -> bool:
    value = getenv(name)
    if value is None:
        raise NoCreds(name)
    return bool(value)


def get_optional_str_env(name: str) -> str | None:
    value = getenv(name)
    return value


def get_optional_int_env(name: str) -> int | None:
    value = getenv(name)
    if value is None:
        return None
    return int(value)


def get_optional_bool_env(name: str) -> bool | None:
    value = getenv(name)
    if value is None:
        return None
    return bool(value)


class TwitchCreds:
    def __init__(self):
        self.__token = get_str_env('TWITCH_TOKEN')
        self.__channel = get_str_env('TWITCH_CHANNEL')

    @property
    def token(self):
        return self.__token

    @property
    def channel(self):
        return self.__channel


class DiscordCreds:
    def __init__(self):
        self.__token = get_optional_str_env('DISCORD_TOKEN')
        self.__queue_channel_id = get_optional_int_env(
            'DISCORD_QUEUE_CHANNEL_ID')
        self.__leaderboard_channel_id = get_optional_int_env(
            'DISCORD_LEADERBOARD_CHANNEL_ID')

    @property
    def token(self):
        return self.__token

    @property
    def queue_channel_id(self):
        return self.__queue_channel_id

    @property
    def leaderboard_channel_id(self):
        return self.__leaderboard_channel_id


class SpotifyCreds:
    def __init__(self):
        self.__client_id = get_str_env('SPOTIFY_CLIENT_ID')
        self.__client_secret = get_str_env('SPOTIFY_SECRET')
        self.__username = get_str_env('SPOTIFY_USERNAME')

    @property
    def client_id(self):
        return self.__client_id

    @property
    def client_secret(self):
        return self.__client_secret

    @property
    def username(self):
        return self.__username


class Creds:
    def __init__(self, log: Log, file: str = './secret/conf.env'):
        self.log = log
        self.file = file
        self.load_env()
        self.twitch: TwitchCreds = TwitchCreds()
        self.discord: DiscordCreds = DiscordCreds()
        self.spotify: SpotifyCreds = SpotifyCreds()

    def load_env(self):
        try:
            load_dotenv(self.file)
        except Exception as e:
            self.log.error('Error loading .env file.')
            raise e
