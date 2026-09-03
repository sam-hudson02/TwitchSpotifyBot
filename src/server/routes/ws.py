from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from server.auth import check_token
from server.state import AppState

router = APIRouter()


@router.websocket('/ws/queue')
async def ws_queue(websocket: WebSocket):
    state: AppState = websocket.app.state.app_state
    # browsers can't set headers on a WebSocket, so the token comes as a query
    # param; fail closed if it is missing/wrong or none is configured
    token = websocket.query_params.get('token')
    if not check_token(state.creds.server_token, token):
        await websocket.close(code=1008)
        return

    await state.queue_socket.connect(websocket)
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
