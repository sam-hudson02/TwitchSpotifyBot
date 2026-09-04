from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from utils import Creds, Settings, DB
from services.interfaces import SpotifyInterface

if TYPE_CHECKING:
    from AudioController.audio_controller import Context


@dataclass
class Services:
    """The shared dependencies every bot is built from."""

    creds: Creds
    settings: Settings
    db: DB
    spotify: SpotifyInterface
    context: 'Context'
