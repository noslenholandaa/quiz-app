import hashlib
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from config import (
    SECRET_KEY,
    REFRESH_SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from database import get_db, UserDB, RefreshTokenDB
from models import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    RefreshTokenInput,
    SessionResponse,
)

logger = logging.getLogger("quizapp.auth")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)
router = APIRouter(prefix="/auth", tags=["auth"])


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire, "type": "access"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token() -> tuple[str, str]:
    raw = os.urandom(64).hex()
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, token_hash


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tipo de token inválido")
        return int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido ou expirado")


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[int]:
    if credentials is None:
        return None
    try:
        return decode_access_token(credentials.credentials)
    except HTTPException:
        return None


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> UserDB:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token não fornecido")
    user_id = decode_access_token(credentials.credentials)
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")
    return user


def build_token_response(user_id: int, db: Session, request: Optional[Request] = None) -> Token:
    access_token = create_access_token(user_id)
    raw_rt, token_hash = create_refresh_token()
    expires = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    rt = RefreshTokenDB(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires,
        user_agent=request.headers.get("user-agent", "")[:500] if request else "",
        ip_address=request.client.host if request and request.client else "",
    )
    db.add(rt)
    db.commit()

    return Token(access_token=access_token, refresh_token=raw_rt)


@router.post("/register", response_model=Token)
def register(data: UserCreate, db: Session = Depends(get_db), request: Request = None):
    existing = db.query(UserDB).filter(UserDB.email == data.email).first()
    if existing:
        logger.warning("Registro duplicado email=%s ip=%s", data.email, request.client.host if request else "?")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email já cadastrado")

    user = UserDB(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("Usuario registrado id=%s email=%s name=\"%s\" ip=%s", user.id, user.email, user.name, request.client.host if request else "?")
    return build_token_response(user.id, db, request)


@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db), request: Request = None):
    user = db.query(UserDB).filter(UserDB.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        logger.warning("Login invalido email=%s ip=%s", data.email, request.client.host if request else "?")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou senha inválidos")

    logger.info("Login sucesso user_id=%s ip=%s", user.id, request.client.host if request else "?")
    return build_token_response(user.id, db, request)


@router.post("/refresh", response_model=Token)
def refresh_token(data: RefreshTokenInput, db: Session = Depends(get_db), request: Request = None):
    token_hash = hashlib.sha256(data.refresh_token.encode()).hexdigest()
    rt = db.query(RefreshTokenDB).filter(
        RefreshTokenDB.token_hash == token_hash,
        RefreshTokenDB.revoked == False,
    ).first()

    if not rt:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido")
    if rt.expires_at < datetime.now(timezone.utc):
        rt.revoked = True
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expirado")

    rt.revoked = True
    rt.last_used_at = datetime.now(timezone.utc)
    db.commit()

    logger.info("Refresh token rotacionado user_id=%s token_id=%s", rt.user_id, rt.id)
    return build_token_response(rt.user_id, db, request)


@router.post("/logout", status_code=204)
def logout(data: RefreshTokenInput, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256(data.refresh_token.encode()).hexdigest()
    rt = db.query(RefreshTokenDB).filter(RefreshTokenDB.token_hash == token_hash).first()
    if rt:
        rt.revoked = True
        db.commit()
        logger.info("Logout user_id=%s token_id=%s", rt.user_id, rt.id)


@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    tokens = (
        db.query(RefreshTokenDB)
        .filter(RefreshTokenDB.user_id == user.id, RefreshTokenDB.revoked == False)
        .order_by(RefreshTokenDB.created_at.desc())
        .all()
    )
    return [
        SessionResponse(
            id=t.id,
            created_at=t.created_at,
            last_used_at=t.last_used_at,
            user_agent=t.user_agent,
            ip_address=t.ip_address,
        )
        for t in tokens
    ]


@router.delete("/sessions/{session_id}", status_code=204)
def revoke_session(session_id: int, user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    rt = db.query(RefreshTokenDB).filter(
        RefreshTokenDB.id == session_id,
        RefreshTokenDB.user_id == user.id,
    ).first()
    if not rt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sessão não encontrada")
    rt.revoked = True
    db.commit()
    logger.info("Sessao revogada user_id=%s session_id=%s", user.id, session_id)


@router.get("/me", response_model=UserResponse)
def me(user: UserDB = Depends(get_current_user)):
    return user
