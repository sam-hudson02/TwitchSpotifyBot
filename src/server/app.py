import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server.state import AppState
from server.routes import (spotify, twitch, discord, queue, leaderboard,
                           playback, settings, users, ws)


def cors_origins() -> list[str]:
    """Allowed browser origins from SERVER_CORS_ORIGINS (comma-separated).
    Defaults to '*' since mutations are already guarded by the bearer token."""
    raw = os.getenv('SERVER_CORS_ORIGINS', '').strip()
    if not raw:
        return ['*']
    return [origin.strip() for origin in raw.split(',') if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = AppState.create()
    app.state.app_state = state
    await state.startup()
    yield
    await state.shutdown()


app = FastAPI(title='Sbotify', lifespan=lifespan)

_origins = cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    # credentials can't be combined with a wildcard origin; the API uses a
    # bearer token in a header rather than cookies, so this is fine
    allow_credentials='*' not in _origins,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(spotify.router)
app.include_router(twitch.router)
app.include_router(discord.router)
app.include_router(queue.router)
app.include_router(leaderboard.router)
app.include_router(playback.router)
app.include_router(settings.router)
app.include_router(users.router)
app.include_router(ws.router)

static_folder = Path(__file__).resolve().parent.parent / 'static'
app.mount('/static', StaticFiles(directory=static_folder), name='static')
