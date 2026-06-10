import os
import logging
import time
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from config import CORS_ORIGINS, RATE_LIMIT_LOGIN_PER_MINUTE, RATE_LIMIT_REGISTER_PER_HOUR, LOG_LEVEL, LOG_FORMAT, ENVIRONMENT, ADMIN_EMAILS
from models import (
    Quiz, QuizCreate, QuizUpdate, QuestionType,
    SubmissionInput, SubmissionResponse, AnswerResponse,
    DashboardResponse, RecentQuizItem, RecentSubmissionItem,
    StatsResponse, PeriodStats,
    AdminDashboardResponse, AdminUserItem,
)
from database import create_db, get_db, seed_quizzes, QuizDB, SubmissionDB, UserDB
from auth import router as auth_router, get_current_user

class StructFormatter(logging.Formatter):
    def format(self, record):
        import json
        return json.dumps({
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }, ensure_ascii=False)


if LOG_FORMAT == "json":
    _fmt = StructFormatter(datefmt="%Y-%m-%dT%H:%M:%S")
else:
    _fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

_handler = logging.StreamHandler()
_handler.setFormatter(_fmt)

logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO), handlers=[_handler])
logger = logging.getLogger("quizapp")

_rate_limit_store: dict = {}


def check_rate_limit(key: str, max_requests: int, window_seconds: int) -> bool:
    now = time.time()
    _rate_limit_store[key] = [t for t in _rate_limit_store.get(key, []) if t > now - window_seconds]
    if len(_rate_limit_store[key]) >= max_requests:
        return False
    _rate_limit_store[key].append(now)
    return True


def migrate_db(db):
    from sqlalchemy import inspect, text
    inspector = inspect(db.bind)
    columns = [c["name"] for c in inspector.get_columns("users")]
    if "role" not in columns:
        dialect = db.bind.dialect.name
        if dialect == "postgresql":
            db.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'user'"))
        else:
            db.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'user'"))
        db.commit()
        logger.info("Coluna 'role' adicionada à tabela users")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando aplicacao (env=%s)", ENVIRONMENT)
    create_db()
    db = next(get_db())
    try:
        migrate_db(db)
        seed_quizzes(db)

        total_users = db.query(UserDB).count()
        if total_users == 0 and ADMIN_EMAILS and not os.getenv("PYTEST_CURRENT_TEST"):
            from auth import hash_password
            admin_email = ADMIN_EMAILS[0].strip()
            if admin_email:
                admin_user = UserDB(
                    name="Administrador",
                    email=admin_email,
                    password_hash=hash_password("admin123"),
                    role="admin",
                )
                db.add(admin_user)
                db.commit()
                logger.info("Conta admin criada: email=%s senha=admin123", admin_email)

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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
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


@app.middleware("http")
async def security_and_logging(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = round((time.time() - start) * 1000)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    if ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    if request.url.path.startswith("/auth/login") or request.url.path.startswith("/auth/register"):
        limit_key = f"auth:{request.client.host}:{request.url.path}"
        max_req = RATE_LIMIT_LOGIN_PER_MINUTE if "login" in request.url.path else RATE_LIMIT_REGISTER_PER_HOUR
        window = 60 if "login" in request.url.path else 3600

        if not check_rate_limit(limit_key, max_req, window):
            logger.warning("Rate limit atingido para %s de %s", request.url.path, request.client.host)
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={"detail": "Muitas tentativas. Aguarde antes de tentar novamente."},
            )

    logger.info("%s %s %s %dms", request.method, request.url.path, response.status_code, elapsed)
    return response


frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

app.include_router(auth_router)


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


def quiz_to_response(q: QuizDB) -> Quiz:
    return Quiz(id=q.id, title=q.title, description=q.description, questions=q.questions)


def require_admin(user: UserDB = Depends(get_current_user)) -> UserDB:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return user


@app.get("/quizzes", response_model=list[Quiz])
def list_quizzes(user=Depends(get_current_user), db: Session = Depends(get_db)):
    mine = db.query(QuizDB).filter(QuizDB.user_id == user.id).all()
    public = db.query(QuizDB).filter(QuizDB.user_id.is_(None)).all()
    seen = set()
    result = []
    for q in public + mine:
        if q.id not in seen:
            seen.add(q.id)
            result.append(quiz_to_response(q))
    return result


@app.get("/quizzes/{quiz_id}", response_model=Quiz)
def get_quiz(quiz_id: int, db: Session = Depends(get_db)):
    q = db.query(QuizDB).filter(QuizDB.id == quiz_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quiz não encontrado")
    return quiz_to_response(q)


@app.post("/quizzes", response_model=Quiz, status_code=201)
def create_quiz(
    data: QuizCreate,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not data.title.strip():
        raise HTTPException(status_code=400, detail="Título é obrigatório")
    if not data.questions:
        raise HTTPException(status_code=400, detail="Adicione ao menos uma pergunta")

    for i, q in enumerate(data.questions):
        if not q.text.strip():
            raise HTTPException(status_code=400, detail=f"Pergunta {i + 1} está vazia")
        if q.type in (QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE, QuestionType.RATING):
            if not q.options or len(q.options) < 2:
                raise HTTPException(
                    status_code=400,
                    detail=f"Pergunta {i + 1} precisa ter ao menos 2 opções",
                )

    q = QuizDB(
        user_id=user.id,
        title=data.title.strip(),
        description=data.description.strip(),
        questions=[q.model_dump() for q in data.questions],
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    logger.info("Quiz criado id=%s usuario=%s titulo=\"%s\"", q.id, user.id, q.title)
    return quiz_to_response(q)


@app.put("/quizzes/{quiz_id}", response_model=Quiz)
def update_quiz(
    quiz_id: int,
    data: QuizUpdate,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(QuizDB).filter(QuizDB.id == quiz_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quiz não encontrado")
    if q.user_id is None:
        raise HTTPException(status_code=403, detail="Quiz padrão não pode ser editado")

    if data.title is not None:
        if not data.title.strip():
            raise HTTPException(status_code=400, detail="Título não pode ficar vazio")
        q.title = data.title.strip()
    if data.description is not None:
        q.description = data.description.strip()
    if data.questions is not None:
        if not data.questions:
            raise HTTPException(status_code=400, detail="Adicione ao menos uma pergunta")
        for i, qu in enumerate(data.questions):
            if not qu.text.strip():
                raise HTTPException(status_code=400, detail=f"Pergunta {i + 1} está vazia")
        q.questions = [qu.model_dump() for qu in data.questions]

    db.commit()
    db.refresh(q)
    logger.info("Quiz atualizado id=%s usuario=%s titulo=\"%s\"", q.id, user.id, q.title)
    return quiz_to_response(q)


@app.delete("/quizzes/{quiz_id}", status_code=204)
def delete_quiz(
    quiz_id: int,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(QuizDB).filter(QuizDB.id == quiz_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quiz não encontrado")
    if q.user_id is None:
        raise HTTPException(status_code=403, detail="Quiz padrão não pode ser removido")

    db.delete(q)
    db.commit()
    logger.info("Quiz removido id=%s usuario=%s", q.id, user.id)


@app.get("/me/quizzes", response_model=list[Quiz])
def list_my_quizzes(
    user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    quizzes = (
        db.query(QuizDB)
        .filter(QuizDB.user_id == user.id)
        .order_by(QuizDB.created_at.desc())
        .all()
    )
    return [quiz_to_response(q) for q in quizzes]


@app.post("/quizzes/{quiz_id}/submit", response_model=SubmissionResponse)
def submit_quiz(
    quiz_id: int,
    submission: SubmissionInput,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    quiz = db.query(QuizDB).filter(QuizDB.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz não encontrado")

    quiz_questions = {q["id"]: q for q in quiz.questions}
    answers_list = []

    for answer_input in submission.answers:
        question = quiz_questions.get(answer_input.question_id)
        if not question:
            raise HTTPException(
                status_code=400,
                detail=f"Pergunta id {answer_input.question_id} não encontrada no quiz",
            )
        answers_list.append(
            AnswerResponse(
                question_id=question["id"],
                question_text=question["text"],
                answer=answer_input.value,
            )
        )

    sub = SubmissionDB(
        user_id=user.id,
        quiz_id=quiz_id,
        quiz_title=quiz.title,
        answers=[a.model_dump() for a in answers_list],
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    return SubmissionResponse(
        id=sub.id,
        user_id=sub.user_id,
        quiz_id=sub.quiz_id,
        quiz_title=sub.quiz_title,
        answers=[AnswerResponse(**a) for a in sub.answers],
        created_at=sub.created_at,
    )


@app.get("/me/submissions", response_model=list[SubmissionResponse])
def list_my_submissions(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    subs = (
        db.query(SubmissionDB)
        .filter(SubmissionDB.user_id == user.id)
        .order_by(SubmissionDB.created_at.desc())
        .all()
    )
    return [
        SubmissionResponse(
            id=s.id,
            user_id=s.user_id,
            quiz_id=s.quiz_id,
            quiz_title=s.quiz_title,
            answers=[AnswerResponse(**a) for a in s.answers],
            created_at=s.created_at,
        )
        for s in subs
    ]


@app.get("/me/dashboard", response_model=DashboardResponse)
def dashboard(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    quizzes_created = db.query(QuizDB).filter(QuizDB.user_id == user.id).count()
    submissions = db.query(SubmissionDB).filter(SubmissionDB.user_id == user.id).all()
    total_submissions = len(submissions)
    responded_quiz_ids = set(s.quiz_id for s in submissions)
    total_quizzes_responded = len(responded_quiz_ids)
    total_answers_submitted = sum(len(s.answers) if isinstance(s.answers, list) else 0 for s in submissions)

    recent_queries = (
        db.query(QuizDB)
        .filter(QuizDB.user_id == user.id)
        .order_by(QuizDB.created_at.desc())
        .limit(5)
        .all()
    )
    recent_subs = (
        db.query(SubmissionDB)
        .filter(SubmissionDB.user_id == user.id)
        .order_by(SubmissionDB.created_at.desc())
        .limit(5)
        .all()
    )

    return DashboardResponse(
        total_quizzes_created=quizzes_created,
        total_quizzes_responded=total_quizzes_responded,
        total_submissions=total_submissions,
        total_answers_submitted=total_answers_submitted,
        recent_quizzes=[RecentQuizItem(id=q.id, title=q.title, created_at=q.created_at) for q in recent_queries],
        recent_submissions=[RecentSubmissionItem(id=s.id, quiz_id=s.quiz_id, quiz_title=s.quiz_title, created_at=s.created_at) for s in recent_subs],
    )


@app.get("/me/stats", response_model=StatsResponse)
def stats(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    subs_7 = db.query(SubmissionDB).filter(
        SubmissionDB.user_id == user.id,
        SubmissionDB.created_at >= seven_days_ago,
    ).count()
    subs_30 = db.query(SubmissionDB).filter(
        SubmissionDB.user_id == user.id,
        SubmissionDB.created_at >= thirty_days_ago,
    ).count()

    qz_7 = db.query(QuizDB).filter(
        QuizDB.user_id == user.id,
        QuizDB.created_at >= seven_days_ago,
    ).count()
    qz_30 = db.query(QuizDB).filter(
        QuizDB.user_id == user.id,
        QuizDB.created_at >= thirty_days_ago,
    ).count()

    return StatsResponse(
        last_7_days=PeriodStats(submissions=subs_7, quizzes_created=qz_7),
        last_30_days=PeriodStats(submissions=subs_30, quizzes_created=qz_30),
    )


@app.get("/health")
def health():
    return {"status": "healthy", "environment": ENVIRONMENT, "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/admin/dashboard", response_model=AdminDashboardResponse)
def admin_dashboard(
    user: UserDB = Depends(require_admin),
    db: Session = Depends(get_db),
):
    total_users = db.query(UserDB).count()
    total_quizzes = db.query(QuizDB).count()
    total_submissions = db.query(SubmissionDB).count()
    users_list = db.query(UserDB).order_by(UserDB.created_at.desc()).all()

    users_data = []
    for u in users_list:
        q_count = db.query(QuizDB).filter(QuizDB.user_id == u.id).count()
        s_count = db.query(SubmissionDB).filter(SubmissionDB.user_id == u.id).count()
        users_data.append(AdminUserItem(
            id=u.id, name=u.name, email=u.email, role=u.role,
            created_at=u.created_at, quizzes_count=q_count, submissions_count=s_count,
        ))

    return AdminDashboardResponse(
        total_users=total_users,
        total_quizzes=total_quizzes,
        total_submissions=total_submissions,
        users=users_data,
    )


@app.get("/admin/users", response_model=list[AdminUserItem])
def admin_list_users(
    user: UserDB = Depends(require_admin),
    db: Session = Depends(get_db),
):
    users_list = db.query(UserDB).order_by(UserDB.created_at.desc()).all()
    result = []
    for u in users_list:
        q_count = db.query(QuizDB).filter(QuizDB.user_id == u.id).count()
        s_count = db.query(SubmissionDB).filter(SubmissionDB.user_id == u.id).count()
        result.append(AdminUserItem(
            id=u.id, name=u.name, email=u.email, role=u.role,
            created_at=u.created_at, quizzes_count=q_count, submissions_count=s_count,
        ))
    return result


@app.put("/admin/users/{user_id}/role")
def admin_set_role(
    user_id: int,
    body: dict,
    user: UserDB = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    new_role = body.get("role")
    if new_role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Role deve ser 'admin' ou 'user'")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="Você não pode alterar seu próprio role")
    target.role = new_role
    db.commit()
    logger.info("Admin %s alterou role do usuario %s para %s", user.id, user_id, new_role)
    return {"detail": f"Role atualizado para {new_role}"}


@app.get("/health/database")
def health_database(db: Session = Depends(get_db)):
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        url_str = str(db.bind.url) if db.bind.url else "unknown"
        if "@" in url_str:
            url_str = url_str.split("@", 1)[0].split("://", 1)[0] + "://<redacted>@" + url_str.split("@", 1)[1]
        return {"status": "healthy", "database": url_str}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    logger.info("Servidor iniciando na porta %s", port)
    uvicorn.run("main:app", host="0.0.0.0", port=port)
