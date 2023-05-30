import json
from enum import Enum
from utils.errors import SettingsError
import os


class Perms(Enum):
    ALL = 'all'
    SUBS = 'subs'
    FOLLOWERS = 'followers'
    PRIVILEGED = 'privileged'


class Reset(Enum):
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'
    OFF = 'off'


class Settings:
    def __init__(self):
        self.__active: bool = False
        self.__dev_mode: bool = False
        self.__permission: Perms = Perms('all')
        self.__veto_pass: int = 5
        self.__leaderboard_reset: Reset = Reset('off')
        self.__leaderboard_rewards: list = []
        self.__leaderboard_announce: bool = False
        self.__discord_bot: bool = True
        self.__log: bool = False
        self.set_settings()

    def save_settings(self):
        settings = {
            'active': int(self.__active),
            'dev mode': int(self.__dev_mode),
            'sr permission': self.__permission.value,
            'veto pass': self.__veto_pass,
            'leaderboard reset': self.__leaderboard_reset.value,
            'leaderboard rewards': self.__leaderboard_rewards,
            'leaderboard announce': int(self.__leaderboard_announce),
            'discord bot': int(self.__discord_bot),
            'log': int(self.__log)
        }
        with open('./data/settings.json', 'w') as s_file:
            json.dump(settings, s_file, indent=4)

    def pull_settings(self):
        if not os.path.exists('./data/settings.json'):
            self.save_settings()

        with open('./data/settings.json') as s_file:
            try:
                return json.load(s_file)
            except json.decoder.JSONDecodeError:
                raise Exception('Settings file is corrupted.')

    def set_settings(self):
        settings = self.pull_settings()
        self.set_active(bool(settings.get('active', False)), save=False)
        self.set_permission(settings.get('sr permission', Perms.ALL),
                            save=False)
        self.set_log(bool(settings.get('log', False)), save=False)
        self.set_dev_mode(bool(settings.get('dev mode', False)), save=False)
        self.set_veto_pass(int(settings.get('veto pass', 5)), save=False)

    def set_active(self, active: bool, save=True):
        self.__active = active
        if save:
            self.save_settings()

    def set_dev_mode(self, dev_mode: bool, save=True):
        self.__dev_mode = dev_mode
        if save:
            self.save_settings()

    def set_permission(self, permission, save=True):
        if type(permission) is Perms:
            self.__permission = permission
            return

        if type(permission) is not str:
            raise SettingsError('Permission must be a string.')

        permission = permission.lower()
        if permission not in ['all', 'subs', 'followers', 'privileged']:
            raise SettingsError('Permission must be either "all", \
                                "subs", "followers" or "privileged".')
        self.__permission = Perms(permission)
        if save:
            self.save_settings()

    def set_veto_pass(self, veto_pass: int, save=True):
        if veto_pass <= 1:
            raise SettingsError('Veto pass must be greater than 1.')
        self.__veto_pass = veto_pass
        if save:
            self.save_settings()

    def set_log(self, log: bool, save=True):
        self.__log = log
        if save:
            self.save_settings()

    @property
    def active(self):
        return self.__active

    @property
    def dev_mode(self):
        return self.__dev_mode

    @property
    def permission(self):
        return self.__permission

    @property
    def veto_pass(self):
        return self.__veto_pass

    @property
    def leaderboard_reset(self):
        return self.__leaderboard_reset

    @property
    def leaderboard_rewards(self):
        return self.__leaderboard_rewards

    @property
    def leaderboard_announce(self):
        return self.__leaderboard_announce

    @property
    def discord_bot(self):
        return self.__discord_bot

    @property
    def log(self):
        return self.__log

    def __str__(self) -> str:
        return f'Active: {self.__active}, Dev mode: {self.__dev_mode}, Veto pass: {self.__veto_pass}, Leaderboard reset: {self.__leaderboard_reset}, \
                Leaderboard rewards: {self.__leaderboard_rewards}, Leaderboard announce: {self.__leaderboard_announce}'
