from fastapi import APIRouter, Depends, HTTPException

from server.deps import get_state, require_auth
from server.models import NowPlaying, ControlResponse
from server.state import AppState

router = APIRouter(tags=['playback'])


@router.get('/now-playing', response_model=NowPlaying)
async def now_playing(state: AppState = Depends(get_state)):
    ctx = state.now_playing()
    return NowPlaying(track=ctx.get('track'),
                      artist=ctx.get('artist'),
                      requester=ctx.get('requester'),
                      album_art=ctx.get('album_art'),
                      progress=ctx.get('progress'),
                      duration=ctx.get('duration'),
                      paused=ctx.get('paused', True),
                      playing_queue=ctx.get('playing_queue', False),
                      live=ctx.get('live', False))


@router.post('/skip', response_model=ControlResponse,
             dependencies=[Depends(require_auth)])
async def skip(state: AppState = Depends(get_state)):
    if not state.twitch_running:
        raise HTTPException(status_code=409,
                            detail='Twitch bot is not running')
    await state.skip()
    return ControlResponse(service='playback', running=True, message='skipped')
