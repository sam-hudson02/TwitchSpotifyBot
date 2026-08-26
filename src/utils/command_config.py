import os
from pathlib import Path
from typing import Any
import yaml


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return '{' + key + '}'


class CommandConfig:
    def __init__(self, path: str = './data/commands.yml'):
        self.path = path
        default_path = Path(__file__).parent / 'default_commands.yml'
        with open(default_path) as f:
            self._defaults: dict[str, Any] = yaml.safe_load(f)
        self._config = self._load()

    def _load(self) -> dict[str, Any]:
        user: dict[str, Any] = {}
        if os.path.exists(self.path):
            with open(self.path) as f:
                user = yaml.safe_load(f) or {}
        merged = self._merge(self._defaults, user)
        if not os.path.exists(self.path):
            os.makedirs(os.path.dirname(self.path) or '.', exist_ok=True)
            with open(self.path, 'w') as f:
                yaml.safe_dump(merged, f, sort_keys=False)
        return merged

    def _merge(self, base: dict, override: dict) -> dict:
        result = dict(base)
        for key, value in override.items():
            if (key in result and isinstance(result[key], dict)
                    and isinstance(value, dict)):
                result[key] = self._merge(result[key], value)
            else:
                result[key] = value
        return result

    def _command(self, command: str) -> dict:
        return self._config.get(command, {})

    def keywords(self, command: str) -> list[str]:
        kws = self._command(command).get('keywords', [])
        return [kws] if isinstance(kws, str) else list(kws)

    def enabled(self, command: str) -> bool:
        return bool(self._command(command).get('enabled', True))

    def message(self, command: str, key: str, **params: Any) -> str:
        safe = _SafeDict(params)
        user = self._command(command).get('messages', {}).get(key)
        default = self._defaults.get(command, {}).get('messages', {}).get(key)
        for template in (user, default, ''):
            if template is None:
                continue
            try:
                return str(template).format_map(safe)
            except (ValueError, IndexError):
                continue
        return ''
