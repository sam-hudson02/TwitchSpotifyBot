from fastapi import APIRouter, Depends, HTTPException

from server.deps import get_state, require_auth
from server.models import SetupStatus, SettingsModel, SettingsUpdate
from server.state import AppState
from utils.errors import SettingsError

router = APIRouter(tags=['settings'])


def _settings_model(state: AppState) -> SettingsModel:
    s = state.settings
    return SettingsModel(active=s.active,
                         dev_mode=s.dev_mode,
                         sr_permission=s.permission.value,
                         veto_pass=s.veto_pass)


@router.get('/setup', response_model=SetupStatus)
async def setup(state: AppState = Depends(get_state)):
    creds = state.creds
    return SetupStatus(
        channel=creds.twitch.channel,
        twitch_configured=bool(creds.twitch.access_token
                               and creds.twitch.refresh_token),
        spotify_configured=bool(creds.spotify.client_id
                                and creds.spotify.client_secret),
        spotify_connected=state.spotify.is_connected(),
        discord_queue_webhook=bool(creds.discord.queue_webhook),
        discord_leaderboard_webhook=bool(creds.discord.leaderboard_webhook),
        server_token_set=bool(creds.server_token))


@router.get('/settings', response_model=SettingsModel)
async def get_settings(state: AppState = Depends(get_state)):
    return _settings_model(state)


@router.put('/settings', response_model=SettingsModel,
            dependencies=[Depends(require_auth)])
async def update_settings(body: SettingsUpdate,
                          state: AppState = Depends(get_state)):
    s = state.settings
    try:
        if body.active is not None:
            state.set_active(body.active)
        if body.dev_mode is not None:
            s.set_dev_mode(body.dev_mode)
        if body.sr_permission is not None:
            s.set_permission(body.sr_permission)
        if body.veto_pass is not None:
            s.set_veto_pass(body.veto_pass)
    except SettingsError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _settings_model(state)
