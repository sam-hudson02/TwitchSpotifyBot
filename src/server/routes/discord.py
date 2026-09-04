from fastapi import APIRouter, Depends, HTTPException

from server.deps import get_state, require_auth
from server.models import DiscordStatus, ControlResponse
from server.state import AppState

router = APIRouter(prefix='/discord', tags=['discord'])


@router.get('/status', response_model=DiscordStatus)
async def discord_status(state: AppState = Depends(get_state)):
    creds = state.creds.discord
    return DiscordStatus(connected=state.discord_running,
                         queue_webhook=creds.queue_webhook is not None,
                         leaderboard_webhook=creds.leaderboard_webhook
                         is not None)


@router.post('/start', response_model=ControlResponse,
             dependencies=[Depends(require_auth)])
async def start_discord(state: AppState = Depends(get_state)):
    if state.discord_running:
        return ControlResponse(service='discord', running=True,
                               message='already running')
    creds = state.creds.discord
    if not (creds.queue_webhook or creds.leaderboard_webhook):
        raise HTTPException(status_code=409,
                            detail='No Discord webhooks configured')
    ok, message = await state.start_discord()
    if not ok:
        raise HTTPException(status_code=502, detail=message)
    return ControlResponse(service='discord', running=True, message=message)


@router.post('/stop', response_model=ControlResponse,
             dependencies=[Depends(require_auth)])
async def stop_discord(state: AppState = Depends(get_state)):
    _, message = await state.stop_discord()
    return ControlResponse(service='discord', running=False, message=message)
