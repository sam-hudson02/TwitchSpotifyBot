import json
from enum import Enum
from utils.errors import SettingsError
import os
import yaml

SETTINGS_FILE = './data/settings.yml'
LEGACY_SETTINGS_FILE = './data/settings.json'

# maps the old settings.json keys to the current settings.yml keys
LEGACY_KEYS = {
    'active': 'ACTIVE',
    'dev mode': 'DEV_MODE',
    'sr permission': 'SR_PERMISSION',
    'veto pass': 'VETO_PASS',
}


class Perms(Enum):
    ALL = 'all'
    SUBS = 'subs'
    FOLLOWERS = 'followers'
    PRIVILEGED = 'privileged'
    DJS = 'djs'


class Settings:
    def __init__(self):
        self.__active: bool = True
        self.__dev_mode: bool = False
        self.__permission: Perms = Perms('all')
        self.__veto_pass: int = 5
        self.set_settings()

    def save_settings(self):
        settings = {
            'ACTIVE': self.__active,
            'DEV_MODE': self.__dev_mode,
            'SR_PERMISSION': self.__permission.value,
            'VETO_PASS': self.__veto_pass
        }
        with open(SETTINGS_FILE, 'w') as s_file:
            yaml.safe_dump(settings, s_file, sort_keys=False)

    def pull_settings(self):
        if not os.path.exists(SETTINGS_FILE):
            if not self.migrate_legacy():
                self.save_settings()

        with open(SETTINGS_FILE) as s_file:
            try:
                return yaml.safe_load(s_file) or {}
            except yaml.YAMLError:
                raise Exception('Settings file is corrupted.')

    def migrate_legacy(self) -> bool:
        if not os.path.exists(LEGACY_SETTINGS_FILE):
            return False
        with open(LEGACY_SETTINGS_FILE) as s_file:
            legacy = json.load(s_file)
        data = {LEGACY_KEYS[k]: v for k, v in legacy.items() if k in LEGACY_KEYS}
        with open(SETTINGS_FILE, 'w') as s_file:
            yaml.safe_dump(data, s_file, sort_keys=False)
        return True

    def set_settings(self):
        settings = self.pull_settings()
        self.set_active(bool(settings.get('ACTIVE', True)), save=False)
        self.set_permission(settings.get('SR_PERMISSION', Perms.ALL),
                            save=False)
        self.set_dev_mode(bool(settings.get('DEV_MODE', False)), save=False)
        self.set_veto_pass(int(settings.get('VETO_PASS', 5)), save=False)

    def set_active(self, active: bool, save=True):
        self.__active = active
        if save:
            self.save_settings()

    def set_dev_mode(self, dev_mode: bool, save=True):
        self.__dev_mode = dev_mode
        if save:
            self.save_settings()

    def set_permission(self, permission, save=True):
        if isinstance(permission, Perms):
            self.__permission = permission
        else:
            if not isinstance(permission, str):
                raise SettingsError('Permission must be a string.')
            permission = permission.lower()
            valid = [p.value for p in Perms]
            if permission not in valid:
                raise SettingsError(
                    f'Permission must be one of {", ".join(valid)}.')
            self.__permission = Perms(permission)
        if save:
            self.save_settings()

    def set_veto_pass(self, veto_pass: int, save=True):
        if veto_pass <= 1:
            raise SettingsError('Veto pass must be greater than 1.')
        self.__veto_pass = veto_pass
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

    def __str__(self) -> str:
        return (f'Active: {self.__active}, Dev mode: {self.__dev_mode}, '
                f'Veto pass: {self.__veto_pass}')
