import os
import time
import uuid
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse

from app.core.config import (
    CORS_ORIGINS, ALLOWED_HOSTS, RATE_LIMIT_LOGIN_PER_MINUTE,
    RATE_LIMIT_REGISTER_PER_HOUR, LOG_LEVEL, LOG_FORMAT, ENVIRONMENT,
    ADMIN_EMAILS, ADMIN_EMAIL, ADMIN_PASSWORD,
)
from app.models.database import create_db, get_db, seed_quizzes, UserDB
from app.utils.logging import setup_logging, set_request_id
from app.middleware.rate_limit import check_rate_limit

_app_start_time: float = time.time()

logger = setup_logging(LOG_FORMAT, LOG_LEVEL)


def run_alembic_migrations():
    try:
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config(os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic.ini"))
        command.upgrade(alembic_cfg, "head")
        logger.info("Migracoes Alembic aplicadas com sucesso")
    except Exception as e:
        logger.warning("Falha ao executar migracoes Alembic: %s. Usando create_all() como fallback.", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando aplicacao (env=%s)", ENVIRONMENT)
    run_alembic_migrations()
    create_db()
    db = next(get_db())
    try:
        seed_quizzes(db)

        total_users = db.query(UserDB).count()
        if total_users == 0 and ADMIN_EMAIL and ADMIN_PASSWORD and not os.getenv("PYTEST_CURRENT_TEST"):
            from app.core.security import hash_password
            admin_user = UserDB(
                name="Administrador",
                email=ADMIN_EMAIL.strip(),
                password_hash=hash_password(ADMIN_PASSWORD),
                role="admin",
            )
            db.add(admin_user)
            db.commit()
            logger.info("Conta admin criada: email=%s", ADMIN_EMAIL.strip())
        elif total_users == 0 and not os.getenv("PYTEST_CURRENT_TEST"):
            logger.info("Nenhum admin criado automaticamente. Defina ADMIN_EMAIL e ADMIN_PASSWORD para criar.")

        promoted = db.query(UserDB).filter(
            UserDB.email.in_(ADMIN_EMAILS),
            UserDB.role != "admin",
        ).update({"role": "admin"}, synchronize_session=False)
        if promoted:
            db.commit()
            logger.info("Usuarios promovidos a admin: %d", promoted)
        logger.info("Banco inicializado com dados padrao")
    finally:
        db.close()
    yield
    logger.info("Aplicacao encerrada")


app = FastAPI(
    title="Quiz App API",
    description="Backend para formulários de pesquisa e quiz",
    lifespan=lifespan,
)

if CORS_ORIGINS == ["*"]:
    if ENVIRONMENT == "production":
        logger.error("CORS configurado com allow_origins=* em producao — bloqueando para seguranca")
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[],
            allow_credentials=False,
            allow_methods=[],
            allow_headers=[],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.warning("CORS configurado com allow_origins=* (apenas para desenvolvimento)")
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    logger.info("CORS configurado com origens: %s", CORS_ORIGINS)

if ALLOWED_HOSTS != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)
    logger.info("TrustedHostMiddleware configurado com hosts: %s", ALLOWED_HOSTS)
else:
    logger.info("TrustedHostMiddleware desativado (permitindo todos os hosts)")


@app.middleware("http")
async def security_and_logging(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    set_request_id(request_id)

    start = time.time()

    if request.url.path.startswith("/auth/login") or request.url.path.startswith("/auth/register"):
        limit_key = f"auth:{request.client.host}:{request.url.path}"
        max_req = RATE_LIMIT_LOGIN_PER_MINUTE if "login" in request.url.path else RATE_LIMIT_REGISTER_PER_HOUR
        window = 60 if "login" in request.url.path else 3600

        if not check_rate_limit(limit_key, max_req, window):
            logger.warning("Rate limit atingido path=%s ip=%s", request.url.path, request.client.host)
            return JSONResponse(
                status_code=429,
                content={"detail": "Muitas tentativas. Aguarde antes de tentar novamente."},
                headers={"X-Request-ID": request_id},
            )

    response = await call_next(request)
    elapsed = round((time.time() - start) * 1000)

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    if ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    logger.info("%s %s %s %dms", request.method, request.url.path, response.status_code, elapsed)
    return response


frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

from app.routers import auth as auth_router
from app.routers import quizzes as quizzes_router
from app.routers import dashboard as dashboard_router
from app.routers import leaderboard as leaderboard_router
from app.routers import admin as admin_router
from app.routers import profile as profile_router
from app.routers import categories as categories_router
from app.routers import health as health_router

app.include_router(auth_router.router)
app.include_router(quizzes_router.router)
app.include_router(dashboard_router.router)
app.include_router(leaderboard_router.router)
app.include_router(admin_router.router)
app.include_router(profile_router.router)
app.include_router(categories_router.router)
app.include_router(health_router.router)


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    logger.info("Servidor iniciando na porta %s", port)
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
