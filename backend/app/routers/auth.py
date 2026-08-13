from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_module
from app.models import User
from app.rate_limit import enforce_login_rate_limit
from app.schemas import LoginRequest, MeResponse, TokenResponse
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(enforce_login_rate_limit)],
)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Benutzername oder Passwort falsch",
        )
    token = create_access_token(user.username)
    return TokenResponse(access_token=token)


@router.get(
    "/me",
    response_model=MeResponse,
    dependencies=[Depends(require_module("core.platform"))],
)
def me(current_user: User = Depends(get_current_user)):
    return MeResponse(username=current_user.username)
