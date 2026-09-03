from fastapi import APIRouter, Depends

from server.deps import get_state
from server.models import QueueItem
from server.state import AppState

router = APIRouter(tags=['queue'])


@router.get('/queue', response_model=list[QueueItem])
async def get_queue(state: AppState = Depends(get_state)):
    return await state.queue_snapshot()
