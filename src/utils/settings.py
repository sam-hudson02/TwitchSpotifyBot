import json
import time
from utils.errors import *
from utils.logger import Log

class Settings:
    def __init__(self, log: Log):
        self.__log = log
        self.__active = False
        self.__dev_mode = False
        self.__veto_pass = 5
        self.__leaderboard_reset = 'off'
        self.__leaderboard_rewards = []
        self.__leaderboard_announce = False
        self.__discord_bot = True
        self.__log = False
        self.set_settings()
    
    def save_settings(self):
        settings = {
            'active': int(self.__active),
            'dev mode': int(self.__dev_mode),
            'veto pass': self.__veto_pass,
            'leaderboard reset': self.__leaderboard_reset,
            'leaderboard rewards': self.__leaderboard_rewards,
            'leaderboard announce': int(self.__leaderboard_announce),
            'discord bot': int(self.__discord_bot),
            'log': self.__log
        }
        with open('./data/settings.json', 'w') as s_file:
            json.dump(settings, s_file, indent=4)

    def setter(func):
        def wrapper(self, *args, **kwargs):
            func(self, *args, **kwargs)
            if kwargs.get('save', True):
                self.save_settings()
        return wrapper

    def pull_settings(self, try_count=0):
        with open('./data/settings.json') as s_file:
            try:
                return json.load(s_file)
            except json.decoder.JSONDecodeError as e:
                if try_count > 3:
                    self.log.error('Error loading settings.json, too many tries.')
                    raise e
                self.log.error('Error loading settings.json, trying again in 5 seconds.')
                time.sleep(5)
                return self.pull_settings(try_count + 1)
            
    
    def set_settings(self):
        settings = self.pull_settings()
        self.set_active(bool(settings.get('active', False)), save=False)
        self.set_discord_bot(bool(settings.get('discord bot', True)), save=False)
        self.set_log(bool(settings.get('log', False)), save=False)
        self.set_dev_mode(bool(settings.get('dev mode', False)), save=False)
        self.set_veto_pass(int(settings.get('veto pass', 5)), save=False)
        self.set_leaderboard_reset(settings.get('leaderboard reset', 'off'), save=False)
        self.set_leaderboard_rewards(settings.get('leaderboard rewards', []), save=False)
        self.set_leaderboard_announce(bool(settings.get('leaderboard announce', False)), save=False)

    @setter
    def set_active(self, active, save=True):
        if type(active) is not bool:
            raise SettingsError('Active must be a boolean.')
        self.__active = active
    
    @setter
    def set_dev_mode(self, dev_mode, save=True):
        if type(dev_mode) is not bool:
            raise SettingsError('Dev mode must be a boolean.')
        self.__dev_mode = dev_mode
    
    @setter
    def set_veto_pass(self, veto_pass, save=True):
        if type(veto_pass) is not int:
            raise SettingsError('Veto pass must be an integer.')
        elif veto_pass < 2:
            raise SettingsError('Veto pass must be greater than 1.')
        self.__veto_pass = veto_pass
    
    @setter
    def set_leaderboard_reset(self, leaderboard_reset, save=True):
        if type(leaderboard_reset) is not str:
            raise SettingsError('Leaderboard reset must be a string.')

        leaderboard_reset = leaderboard_reset.lower()

        accepted = ['weekly', 'monthly', 'off']
        if leaderboard_reset not in accepted:
            raise SettingsError(f"Leaderboard reset must be either {' or '.join(accepted)}")
        self.__leaderboard_reset = leaderboard_reset
    
    @setter
    def set_leaderboard_rewards(self, leaderboard_rewards, save=True):
        if type(leaderboard_rewards) is not list:
            raise SettingsError('Leaderboard rewards must be a list.')
        for item in leaderboard_rewards:
            if item not in ['vip', 'sp_mod']:
                raise SettingsError('Leaderboard rewards must only contain "vip" or "sp_mod".')
        self.__leaderboard_rewards = leaderboard_rewards

    @setter
    def set_leaderboard_announce(self, leaderboard_announce, save=True):
        if type(leaderboard_announce) is not bool:
            raise SettingsError('Leaderboard announce must be a boolean.')
        self.__leaderboard_announce = leaderboard_announce

    @setter
    def set_discord_bot(self, discord_bot, save=True):
        if type(discord_bot) is not bool:
            raise SettingsError('Discord bot must be a boolean.')
        self.__discord_bot = discord_bot

    @setter
    def set_log(self, log, save=True):
        if type(log) is not bool:
            raise SettingsError('Log must be a boolean.')
        self.__log = log

    @property
    def active(self):
        return self.__active
    
    @property
    def dev_mode(self):
        return self.__dev_mode
    
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
