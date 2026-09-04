from fastapi import Request, Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from server.auth import check_token
from server.state import AppState

bearer = HTTPBearer(auto_error=False)


def get_state(request: Request) -> AppState:
    return request.app.state.app_state


def require_auth(
    state: AppState = Depends(get_state),
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
) -> None:
    configured = state.creds.server_token
    if not configured:
        raise HTTPException(status_code=503,
                            detail='Server auth is not configured; set '
                                   'SERVER_API_TOKEN')
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail='Missing bearer token')
    if not check_token(configured, credentials.credentials):
        raise HTTPException(status_code=403, detail='Invalid token')
