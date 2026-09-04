from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from server.auth import check_token
from server.state import AppState

router = APIRouter()


def token_from_subprotocols(subprotocols: list[str]) -> str | None:
    """The token is sent as a `bearer` subprotocol pair so it rides in the
    Sec-WebSocket-Protocol header rather than the URL (which gets logged).
    Clients offer ['bearer', '<token>']."""
    if len(subprotocols) >= 2 and subprotocols[0] == 'bearer':
        return subprotocols[1]
    return None


@router.websocket('/ws/queue')
async def ws_queue(websocket: WebSocket):
    state: AppState = websocket.app.state.app_state
    token = token_from_subprotocols(websocket.scope.get('subprotocols', []))
    if not check_token(state.creds.server_token, token):
        await websocket.close(code=1008)
        return

    # echo back only the 'bearer' marker, never the token itself
    await state.queue_socket.connect(websocket, subprotocol='bearer')
    try:
        while True:
            data = await websocket.receive_json()
            try:
                await handle(state, data)
            except Exception as e:
                await websocket.send_json({'error': str(e)})
    except WebSocketDisconnect:
        state.queue_socket.disconnect(websocket)


async def handle(state: AppState, data: dict) -> None:
    op = data.get('op')
    if op == 'move':
        after = data.get('after')
        await state.queue_move(int(data['id']),
                               None if after is None else int(after))
    elif op == 'remove':
        await state.queue_remove(int(data['id']))
    elif op == 'clear':
        await state.queue_clear()
    else:
        raise ValueError(f'unknown op: {op}')
