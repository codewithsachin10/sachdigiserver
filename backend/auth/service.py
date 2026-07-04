from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.database import verify_user, set_session_token, get_user_by_token

security = HTTPBearer(auto_error=False)

def authenticate_user(username: str, password: str):
    user = verify_user(username, password)
    if not user:
        return None
    token = set_session_token(username)
    return {"username": user["username"], "token": token}

def get_current_user(request: Request, auth: HTTPAuthorizationCredentials = Depends(security)):
    token = None
    if auth:
        token = auth.credentials
    if not token:
        token = request.query_params.get("token")
    if not token:
        token = request.cookies.get("sach_session")
        
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials missing."
        )
        
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token."
        )
    return user
