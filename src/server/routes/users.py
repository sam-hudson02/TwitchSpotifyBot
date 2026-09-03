from fastapi import APIRouter, Depends

from server.deps import get_state, require_auth
from server.models import UserModel
from server.state import AppState

router = APIRouter(prefix='/users', tags=['users'],
                   dependencies=[Depends(require_auth)])


def _user_model(user) -> UserModel:
    return UserModel(username=user.username, ban=user.ban, dj=user.dj,
                     admin=user.admin, requests=user.requests,
                     rates=user.rates)


@router.get('', response_model=list[UserModel])
async def list_users(state: AppState = Depends(get_state)):
    return [_user_model(u) for u in await state.db.get_all_users()]


@router.put('/{username}/ban', response_model=UserModel)
async def ban_user(username: str, state: AppState = Depends(get_state)):
    return _user_model(await state.set_user_flags(username, ban=True))


@router.put('/{username}/unban', response_model=UserModel)
async def unban_user(username: str, state: AppState = Depends(get_state)):
    return _user_model(await state.set_user_flags(username, ban=False))


@router.put('/{username}/dj', response_model=UserModel)
async def make_dj(username: str, state: AppState = Depends(get_state)):
    return _user_model(await state.set_user_flags(username, dj=True))


@router.put('/{username}/undj', response_model=UserModel)
async def remove_dj(username: str, state: AppState = Depends(get_state)):
    return _user_model(await state.set_user_flags(username, dj=False))
