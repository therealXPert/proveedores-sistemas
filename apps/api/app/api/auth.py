from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.auth import LoginRequest, TokenResponse, CurrentUser
from app.services.auth_service import authenticate_user, build_token_for_user
from app.api.deps import get_current_user
from app.models.security import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )
    token = build_token_for_user(user)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=CurrentUser)
def me(current_user: User = Depends(get_current_user)):
    return CurrentUser(
        id=current_user.id,
        email=current_user.email,
        nombre=current_user.nombre,
        roles=current_user.roles,
    )
