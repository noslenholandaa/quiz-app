import hashlib
import logging
import os
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import (
    REFRESH_TOKEN_EXPIRE_DAYS, ADMIN_EMAILS, ENVIRONMENT,
    FRONTEND_URL,
)
from app.core.security import (
    hash_password, verify_password, create_access_token, create_refresh_token,
)
from app.models.database import UserDB, RefreshTokenDB, PasswordResetTokenDB
from app.schemas.models import (
    UserCreate, UserLogin, Token, RefreshTokenInput,
    ResetPasswordInput, SessionResponse, ForgotPasswordInput, ForgotPasswordResponse,
)
logger = logging.getLogger("quizapp.auth")

PASSWORD_RESET_EXPIRE_HOURS = 1


def build_token_response(user_id: int, role: str, db: Session, request: Request = None) -> Token:
    access_token = create_access_token(user_id, role)
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


def register(data: UserCreate, db: Session, request: Request = None) -> Token:
    existing = db.query(UserDB).filter(UserDB.email == data.email).first()
    if existing:
        logger.warning("Registro duplicado email=%s ip=%s", data.email, request.client.host if request else "?")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email já cadastrado")

    if not data.name.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Nome não pode ficar vazio")
    if not data.password.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Senha não pode ficar vazia")
    if len(data.password.strip()) < 6:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Senha deve ter no mínimo 6 caracteres")

    role = "admin" if data.email.lower() in ADMIN_EMAILS else "user"

    user = UserDB(
        name=data.name.strip(),
        email=data.email,
        password_hash=hash_password(data.password.strip()),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("Usuario registrado id=%s email=%s name=\"%s\" role=%s ip=%s", user.id, user.email, user.name, user.role, request.client.host if request else "?")
    return build_token_response(user.id, user.role, db, request)


def login(data: UserLogin, db: Session, request: Request = None) -> Token:
    from app.core.security import DUMMY_PASSWORD_HASH
    user = db.query(UserDB).filter(UserDB.email == data.email).first()
    if not user:
        verify_password(data.password, DUMMY_PASSWORD_HASH)
        logger.warning("Login invalido email=%s ip=%s", data.email, request.client.host if request else "?")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou senha inválidos")

    if not verify_password(data.password.strip(), user.password_hash):
        logger.warning("Login invalido email=%s ip=%s", data.email, request.client.host if request else "?")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou senha inválidos")

    logger.info("Login sucesso user_id=%s ip=%s", user.id, request.client.host if request else "?")
    return build_token_response(user.id, user.role, db, request)


def refresh_token(data: RefreshTokenInput, db: Session, request: Request = None) -> Token:
    from app.core.config import REFRESH_SECRET_KEY
    token_hash = hashlib.sha256((data.refresh_token + REFRESH_SECRET_KEY).encode()).hexdigest()
    rt = db.query(RefreshTokenDB).filter(
        RefreshTokenDB.token_hash == token_hash,
        RefreshTokenDB.revoked.is_(False),
    ).first()

    if not rt:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido")
    if rt.expires_at.replace(tzinfo=None) < datetime.now(timezone.utc).replace(tzinfo=None):
        rt.revoked = True
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expirado")

    rt.revoked = True
    rt.last_used_at = datetime.now(timezone.utc)
    db.commit()

    logger.info("Refresh token rotacionado user_id=%s token_id=%s", rt.user_id, rt.id)
    user = db.query(UserDB).filter(UserDB.id == rt.user_id).first()
    return build_token_response(rt.user_id, user.role if user else "user", db, request)


def logout(refresh_token_str: str, db: Session):
    from app.core.config import REFRESH_SECRET_KEY
    token_hash = hashlib.sha256((refresh_token_str + REFRESH_SECRET_KEY).encode()).hexdigest()
    rt = db.query(RefreshTokenDB).filter(RefreshTokenDB.token_hash == token_hash).first()
    if rt:
        rt.revoked = True
        db.commit()
        logger.info("Logout user_id=%s token_id=%s", rt.user_id, rt.id)


def list_sessions(user: UserDB, db: Session) -> list[SessionResponse]:
    tokens = (
        db.query(RefreshTokenDB)
        .filter(RefreshTokenDB.user_id == user.id, RefreshTokenDB.revoked.is_(False))
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


def revoke_session(session_id: int, user: UserDB, db: Session):
    rt = db.query(RefreshTokenDB).filter(
        RefreshTokenDB.id == session_id,
        RefreshTokenDB.user_id == user.id,
    ).first()
    if not rt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sessão não encontrada")
    rt.revoked = True
    db.commit()
    logger.info("Sessao revogada user_id=%s session_id=%s", user.id, session_id)


def forgot_password(data: ForgotPasswordInput, db: Session, request: Request = None) -> ForgotPasswordResponse:
    message = "Se o email existir, instruções foram enviadas."
    user = db.query(UserDB).filter(UserDB.email == data.email).first()
    reset_url: str | None = None
    if user:
        raw = os.urandom(32).hex()
        token_hash = hashlib.sha256(raw.encode()).hexdigest()
        expires = datetime.now(timezone.utc) + timedelta(hours=PASSWORD_RESET_EXPIRE_HOURS)
        reset = PasswordResetTokenDB(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires,
        )
        db.add(reset)
        db.commit()
        base_url = FRONTEND_URL or ""
        reset_url = f"{base_url}/static/reset-password.html?token={raw}"
        logger.info(
            "Password reset token generated for user %s (email=%s). "
            "Demo mode — reset URL: %s",
            user.id, data.email, reset_url,
        )
    from app.core.security import DUMMY_PASSWORD_HASH
    import bcrypt
    bcrypt.checkpw(b"dummy", DUMMY_PASSWORD_HASH.encode("utf-8"))
    return ForgotPasswordResponse(message=message, reset_url=reset_url)


def reset_password(data: ResetPasswordInput, db: Session):
    token_hash = hashlib.sha256(data.token.encode()).hexdigest()
    reset = db.query(PasswordResetTokenDB).filter(
        PasswordResetTokenDB.token_hash == token_hash,
        PasswordResetTokenDB.used.is_(False),
    ).first()

    if not reset:
        raise HTTPException(status_code=400, detail="Token inválido")
    if reset.expires_at.replace(tzinfo=None) < datetime.now(timezone.utc).replace(tzinfo=None):
        reset.used = True
        db.commit()
        raise HTTPException(status_code=400, detail="Token expirado")
    if not data.new_password.strip() or len(data.new_password.strip()) < 6:
        raise HTTPException(status_code=422, detail="Senha deve ter no mínimo 6 caracteres")

    user = db.query(UserDB).filter(UserDB.id == reset.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="Usuário não encontrado")

    user.password_hash = hash_password(data.new_password.strip())
    reset.used = True
    db.commit()

    logger.info("Senha redefinida user_id=%s", user.id)
    return {"message": "Senha redefinida com sucesso."}


def dev_get_reset_url(email: str, user: UserDB, db: Session):
    if ENVIRONMENT == "production":
        raise HTTPException(status_code=404, detail="Not found")
    if user.role != "admin" and user.email != email:
        raise HTTPException(status_code=403, detail="Acesso negado")
    target = db.query(UserDB).filter(UserDB.email == email).first()
    if not target:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    raw = os.urandom(32).hex()
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    expires = datetime.now(timezone.utc) + timedelta(hours=PASSWORD_RESET_EXPIRE_HOURS)
    reset = PasswordResetTokenDB(
        user_id=target.id,
        token_hash=token_hash,
        expires_at=expires,
    )
    db.add(reset)
    db.commit()
    logger.info("[DEV] Reset token generated via dev endpoint for user %s", target.id)
    return {"reset_url": f"/static/reset-password.html?token={raw}"}
