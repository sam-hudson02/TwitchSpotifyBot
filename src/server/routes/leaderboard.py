from fastapi import APIRouter, Depends

from server.deps import get_state
from server.models import LeaderboardEntry
from server.state import AppState

router = APIRouter(tags=['leaderboard'])


@router.get('/leaderboard', response_model=list[LeaderboardEntry])
async def get_leaderboard(state: AppState = Depends(get_state)):
    board = await state.db.get_leaderboard()
    return [LeaderboardEntry(position=i + 1,
                             username=user.username,
                             rates=user.rates,
                             requests=user.requests)
            for i, user in enumerate(board.sorted)]
