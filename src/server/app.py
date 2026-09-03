from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from server.state import AppState
from server.routes import (spotify, twitch, discord, queue, leaderboard,
                           playback, ws)


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = AppState.create()
    app.state.app_state = state
    await state.startup()
    yield
    await state.shutdown()


app = FastAPI(title='Sbotify', lifespan=lifespan)

app.include_router(spotify.router)
app.include_router(twitch.router)
app.include_router(discord.router)
app.include_router(queue.router)
app.include_router(leaderboard.router)
app.include_router(playback.router)
app.include_router(ws.router)

static_folder = Path(__file__).resolve().parent.parent / 'static'
app.mount('/static', StaticFiles(directory=static_folder), name='static')
