import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.models.database import get_db, UserDB
from app.schemas.models import (
    UserCreate, UserLogin, UserResponse, Token, RefreshTokenInput,
    SessionResponse, ForgotPasswordInput, ForgotPasswordResponse,
    ResetPasswordInput,
)
from app.services import auth_service

logger = logging.getLogger("quizapp.auth")
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token)
def register(data: UserCreate, db: Session = Depends(get_db), request: Request = None):
    return auth_service.register(data, db, request)


@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db), request: Request = None):
    return auth_service.login(data, db, request)


@router.post("/refresh", response_model=Token)
def refresh_token(data: RefreshTokenInput, db: Session = Depends(get_db), request: Request = None):
    return auth_service.refresh_token(data, db, request)


@router.post("/logout", status_code=204)
def logout(data: RefreshTokenInput, db: Session = Depends(get_db)):
    auth_service.logout(data.refresh_token, db)


@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    return auth_service.list_sessions(user, db)


@router.delete("/sessions/{session_id}", status_code=204)
def revoke_session(session_id: int, user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    auth_service.revoke_session(session_id, user, db)


@router.get("/me", response_model=UserResponse)
def me(user: UserDB = Depends(get_current_user)):
    return user


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(data: ForgotPasswordInput, db: Session = Depends(get_db), request: Request = None):
    return auth_service.forgot_password(data, db, request)


@router.post("/reset-password")
def reset_password(data: ResetPasswordInput, db: Session = Depends(get_db)):
    return auth_service.reset_password(data, db)


@router.get("/dev/reset-url", include_in_schema=False)
def dev_get_reset_url(
    email: str,
    user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return auth_service.dev_get_reset_url(email, user, db)
