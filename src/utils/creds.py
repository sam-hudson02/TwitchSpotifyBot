from dotenv import load_dotenv
from utils.errors import NoCreds
from utils.logger import Log
from os import getenv


class TwitchCreds:
    def __init__(self, log: Log):
        self.log = log
        self.__token= getenv('TWITCH_TOKEN')
        self.__channel = getenv('TWITCH_CHANNEL')
    
    @property
    def token(self):
        if self.__token is None:
            self.log.critical('Twitch token missing! Not continuing.')
            raise NoCreds('Twitch Token')
        return self.__token
    
    @property
    def channel(self):
        if self.__channel is None:
            self.log.critical('Twitch channel missing! Not continuing.')
            raise NoCreds('Twitch Channel')
        return self.__channel


class DiscordCreds:
    def __init__(self, log: Log):
        self.log = log
        self.__token = getenv('DISCORD_TOKEN')
        self.__queue_channel_id = getenv('DISCORD_QUEUE_CHANNEL_ID')
        self.__leaderboard_channel_id = getenv('DISCORD_LEADERBOARD_CHANNEL_ID')

    @property
    def token(self):
        if self.__token is None:
            self.log.critical('Discord token missing!')
        return self.__token
    
    @property
    def queue_channel_id(self):
        if self.__queue_channel_id is None:
            self.log.critical('Discord queue channel id missing!')
        return self.__queue_channel_id
    
    @property
    def leaderboard_channel_id(self):
        if self.__leaderboard_channel_id is None:
            self.log.critical('Discord leaderboard channel id missing!')
        return self.__leaderboard_channel_id

    def creds_valid(self) -> bool:
        if self.__token is None or self.__queue_channel_id is None or self.__leaderboard_channel_id is None:
            return False
        return True


class SpotifyCreds:
    def __init__(self, log: Log):
        self.log = log
        self.__client_id = getenv('SPOTIFY_CLIENT_ID')
        self.__client_secret = getenv('SPOTIFY_SECRET')
        self.__username = getenv('SPOTIFY_USERNAME')

    @property
    def client_id(self):
        if self.__client_id is None:
            self.log.critical('Spotify client id missing! Not continuing.')
            raise NoCreds('Spotify Client ID')
        return self.__client_id
    
    @property
    def client_secret(self):
        if self.__client_secret is None:
            self.log.critical('Spotify client secret missing! Not continuing.')
            raise NoCreds('Spotify Client Secret')
        return self.__client_secret
    
    @property
    def username(self):
        if self.__username is None:
            self.log.critical('Spotify username missing! Not continuing.')
            raise NoCreds('Spotify Username')
        return self.__username


class Creds:
    def __init__(self, log: Log, file: str = './secret/conf.env'):
        self.log = log
        self.file = file
        self.load_env()
        self.twitch: TwitchCreds = TwitchCreds(self.log)
        self.discord: DiscordCreds = DiscordCreds(self.log)
        self.spotify: SpotifyCreds = SpotifyCreds(self.log)
        
    def load_env(self):
        try:
            load_dotenv(self.file)
        except Exception as e:
            self.log.error('Error loading .env file.')
            raise e
