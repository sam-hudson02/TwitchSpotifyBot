import asyncio

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, PlainTextResponse

from server.deps import get_state
from server.models import SpotifyStatus
from server.state import AppState

router = APIRouter(tags=['spotify'])


@router.get('/spotify/status', response_model=SpotifyStatus)
async def spotify_status(state: AppState = Depends(get_state)):
    # spotipy is blocking, so verify off the event loop
    working = await asyncio.to_thread(state.spotify.verify)
    return SpotifyStatus(connected=state.spotify.is_connected(),
                         working=working,
                         user=state.creds.spotify.username)


@router.get('/')
async def index(request: Request, state: AppState = Depends(get_state)):
    if not state.spotify.is_connected():
        return RedirectResponse(
            state.spotify.authorize_url(str(request.base_url)))
    await state.start_twitch()
    return PlainTextResponse('Bot is running')


@router.get('/callback')
async def callback(request: Request, state: AppState = Depends(get_state)):
    # spotipy exchanges the code and verifies the token synchronously
    ok = await asyncio.to_thread(state.spotify.handle_callback, str(request.url))
    if not ok:
        return PlainTextResponse(
            'Connected to Spotify but the credentials could not be verified. '
            'Check your Spotify app settings and try again.', status_code=400)
    await state.start_twitch()
    return PlainTextResponse('Bot is running')
