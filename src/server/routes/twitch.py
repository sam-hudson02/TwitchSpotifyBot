from fastapi import APIRouter, Depends, HTTPException

from server.deps import get_state, require_auth
from server.models import TwitchStatus, ControlResponse, ActiveUpdate
from server.state import AppState

router = APIRouter(prefix='/twitch', tags=['twitch'])


@router.get('/status', response_model=TwitchStatus)
async def twitch_status(state: AppState = Depends(get_state)):
    if not state.twitch_running:
        return TwitchStatus(running=False, channel=state.creds.twitch.channel)
    return TwitchStatus(running=True,
                        channel=state.creds.twitch.channel,
                        bot_name=state.creds.twitch.bot_name,
                        live=state.twitch.live,
                        active=state.twitch.active)


@router.post('/start', response_model=ControlResponse,
             dependencies=[Depends(require_auth)])
async def start_twitch(state: AppState = Depends(get_state)):
    if state.twitch_running:
        return ControlResponse(service='twitch', running=True,
                               message='already running')
    if not state.spotify.is_connected():
        raise HTTPException(status_code=409,
                            detail='Spotify is not connected; authorize '
                                   'Spotify before starting the Twitch bot')
    ok, message = await state.start_twitch()
    if not ok:
        raise HTTPException(status_code=502, detail=message)
    return ControlResponse(service='twitch', running=True, message=message)


@router.post('/stop', response_model=ControlResponse,
             dependencies=[Depends(require_auth)])
async def stop_twitch(state: AppState = Depends(get_state)):
    _, message = await state.stop_twitch()
    return ControlResponse(service='twitch', running=False, message=message)


@router.put('/active', response_model=ActiveUpdate,
            dependencies=[Depends(require_auth)])
async def set_active(body: ActiveUpdate, state: AppState = Depends(get_state)):
    state.set_active(body.active)
    return ActiveUpdate(active=state.settings.active)
