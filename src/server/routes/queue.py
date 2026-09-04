from fastapi import APIRouter, Depends, HTTPException

from server.deps import get_state, require_auth
from server.models import QueueItem, QueueAdd, QueueMove
from server.state import AppState
from utils.errors import (BadLink, TrackNotFound, YoutubeLink,
                          UnsupportedLink, TrackAlreadyInQueue)

router = APIRouter(tags=['queue'])


@router.get('/queue', response_model=list[QueueItem])
async def get_queue(state: AppState = Depends(get_state)):
    return await state.queue_snapshot()


@router.post('/queue', response_model=list[QueueItem],
             dependencies=[Depends(require_auth)])
async def add_to_queue(body: QueueAdd, state: AppState = Depends(get_state)):
    if not state.twitch_running:
        raise HTTPException(status_code=409, detail='Twitch bot is not running')
    try:
        await state.queue_add(body.query)
    except (TrackNotFound, BadLink):
        raise HTTPException(status_code=404, detail='Could not find that song')
    except (YoutubeLink, UnsupportedLink):
        raise HTTPException(status_code=400,
                            detail='Only Spotify tracks are supported')
    except TrackAlreadyInQueue:
        raise HTTPException(status_code=409,
                            detail='That song is already in the queue')
    return await state.queue_snapshot()


@router.put('/queue/{req_id}', response_model=list[QueueItem],
            dependencies=[Depends(require_auth)])
async def move_in_queue(req_id: int, body: QueueMove,
                        state: AppState = Depends(get_state)):
    try:
        await state.queue_move(req_id, body.after)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return await state.queue_snapshot()


@router.delete('/queue', response_model=list[QueueItem],
               dependencies=[Depends(require_auth)])
async def clear_queue(state: AppState = Depends(get_state)):
    await state.queue_clear()
    return await state.queue_snapshot()


@router.delete('/queue/{req_id}', response_model=list[QueueItem],
               dependencies=[Depends(require_auth)])
async def remove_from_queue(req_id: int, state: AppState = Depends(get_state)):
    await state.queue_remove(req_id)
    return await state.queue_snapshot()
