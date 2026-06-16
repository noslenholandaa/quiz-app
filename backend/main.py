import os
import logging
import time
import uuid
from pathlib import Path
from contextvars import ContextVar
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session, selectinload

from config import (
    CORS_ORIGINS, ALLOWED_HOSTS, RATE_LIMIT_LOGIN_PER_MINUTE,
    RATE_LIMIT_REGISTER_PER_HOUR, LOG_LEVEL, LOG_FORMAT, ENVIRONMENT,
    ADMIN_EMAILS, ADMIN_EMAIL, ADMIN_PASSWORD, APP_VERSION,
)
from models import (
    Quiz, QuizCreate, QuizUpdate, QuestionType,
    SubmissionInput, SubmissionResponse, AnswerResponse,
    DashboardResponse, RecentQuizItem, RecentSubmissionItem,
    StatsResponse, PeriodStats,
    AdminDashboardResponse, AdminUserItem,
    LeaderboardEntry, QuizLeaderboardEntry, PublicProfileResponse, Badge,
    CategoryResponse, TagResponse, SearchResult, SubmissionListResponse,
)
from sqlalchemy import func, or_
from database import create_db, get_db, seed_quizzes, QuizDB, SubmissionDB, UserDB, CategoryDB, TagDB
from auth import router as auth_router, get_current_user

_app_start_time: float = time.time()
_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = _request_id_ctx.get()
        return True


class StructFormatter(logging.Formatter):
    def format(self, record):
        import json
        return json.dumps({
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", ""),
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }, ensure_ascii=False)


if LOG_FORMAT == "json":
    _fmt = StructFormatter(datefmt="%Y-%m-%dT%H:%M:%S")
else:
    _fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | [%(request_id)s] | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

_handler = logging.StreamHandler()
_handler.setFormatter(_fmt)
_handler.addFilter(RequestIdFilter())

logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO), handlers=[_handler])
logger = logging.getLogger("quizapp")

_rate_limit_store: dict = {}
_rate_limit_last_gc: float = 0.0
_RATE_LIMIT_GC_INTERVAL: float = 300.0


def _rate_limit_gc():
    global _rate_limit_last_gc
    now = time.time()
    if now - _rate_limit_last_gc < _RATE_LIMIT_GC_INTERVAL:
        return
    _rate_limit_last_gc = now
    keys_to_delete = []
    for key, timestamps in _rate_limit_store.items():
        _rate_limit_store[key] = [t for t in timestamps if t > now - 3600]
        if not _rate_limit_store[key]:
            keys_to_delete.append(key)
    for key in keys_to_delete:
        del _rate_limit_store[key]


def check_rate_limit(key: str, max_requests: int, window_seconds: int) -> bool:
    _rate_limit_gc()
    now = time.time()
    _rate_limit_store[key] = [t for t in _rate_limit_store.get(key, []) if t > now - window_seconds]
    if len(_rate_limit_store[key]) >= max_requests:
        return False
    _rate_limit_store[key].append(now)
    return True


def run_alembic_migrations():
    try:
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "alembic.ini"))
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
            from auth import hash_password
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
    _request_id_ctx.set(request_id)

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


frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

app.include_router(auth_router)


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


def quiz_to_response(q: QuizDB) -> Quiz:
    category = CategoryResponse.model_validate(q.category) if q.category else None
    tags = [TagResponse.model_validate(t) for t in q.tags] if q.tags else []
    return Quiz(
        id=q.id, title=q.title, description=q.description,
        questions=q.questions, category=category, tags=tags, views=q.views,
    )


def require_admin(user: UserDB = Depends(get_current_user)) -> UserDB:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return user


@app.get("/quizzes", response_model=list[Quiz])
def list_quizzes(user=Depends(get_current_user), db: Session = Depends(get_db)):
    mine = db.query(QuizDB).options(selectinload(QuizDB.category), selectinload(QuizDB.tags)).filter(QuizDB.user_id == user.id).all()
    public = db.query(QuizDB).options(selectinload(QuizDB.category), selectinload(QuizDB.tags)).filter(QuizDB.user_id.is_(None)).all()
    seen = set()
    result = []
    for q in public + mine:
        if q.id not in seen:
            seen.add(q.id)
            result.append(quiz_to_response(q))
    return result


@app.get("/quizzes/search", response_model=SearchResult)
def search_quizzes(
    q: str = "",
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    limit = min(limit, 100)
    offset = (page - 1) * limit
    query = db.query(QuizDB).filter(QuizDB.user_id == user.id)
    if q:
        like_pattern = f"%{q}%"
        query = query.filter(
            or_(
                QuizDB.title.ilike(like_pattern),
                QuizDB.description.ilike(like_pattern),
                QuizDB.tags.any(TagDB.name.ilike(like_pattern)),
            )
        )
    total = query.count()
    items = query.options(selectinload(QuizDB.category), selectinload(QuizDB.tags)).order_by(QuizDB.created_at.desc()).offset(offset).limit(limit).all()
    return SearchResult(
        items=[quiz_to_response(q) for q in items],
        page=page, limit=limit, total=total,
    )



@app.get("/quizzes/{quiz_id}", response_model=Quiz)
def get_quiz(quiz_id: int, db: Session = Depends(get_db)):
    q = db.query(QuizDB).options(selectinload(QuizDB.category), selectinload(QuizDB.tags)).filter(QuizDB.id == quiz_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quiz não encontrado")
    q.views = (q.views or 0) + 1
    db.commit()
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
        category_id=data.category_id,
    )
    if data.tag_ids:
        tags = db.query(TagDB).filter(TagDB.id.in_(data.tag_ids)).all()
        q.tags = tags
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
    if q.user_id != user.id:
        raise HTTPException(status_code=403, detail="Você não tem permissão para editar este quiz")

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
    if data.category_id is not None:
        cat = db.query(CategoryDB).filter(CategoryDB.id == data.category_id).first()
        if not cat:
            raise HTTPException(status_code=400, detail="Categoria não encontrada")
        q.category_id = data.category_id
    if data.tag_ids is not None:
        tags = db.query(TagDB).filter(TagDB.id.in_(data.tag_ids)).all()
        q.tags = tags

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
    if q.user_id != user.id:
        raise HTTPException(status_code=403, detail="Você não tem permissão para remover este quiz")

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
        .options(selectinload(QuizDB.category), selectinload(QuizDB.tags))
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

    max_score = len(quiz.questions)
    score = len(answers_list)
    percentage = round((score / max_score) * 100) if max_score > 0 else 0

    sub = SubmissionDB(
        user_id=user.id,
        quiz_id=quiz_id,
        quiz_title=quiz.title,
        answers=[a.model_dump() for a in answers_list],
        score=score,
        max_score=max_score,
        percentage=percentage,
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
        score=sub.score,
        max_score=sub.max_score,
        percentage=sub.percentage,
        created_at=sub.created_at,
    )


@app.get("/me/submissions", response_model=SubmissionListResponse)
def list_my_submissions(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = 1,
    limit: int = 20,
):
    limit = min(limit, 100)
    offset = (page - 1) * limit
    base = db.query(SubmissionDB).filter(SubmissionDB.user_id == user.id)
    total = base.count()
    subs = base.order_by(SubmissionDB.created_at.desc()).offset(offset).limit(limit).all()
    return SubmissionListResponse(
        items=[
            SubmissionResponse(
                id=s.id,
                user_id=s.user_id,
                quiz_id=s.quiz_id,
                quiz_title=s.quiz_title,
                answers=[AnswerResponse(**a) for a in s.answers],
                score=s.score,
                max_score=s.max_score,
                percentage=s.percentage,
                created_at=s.created_at,
            )
            for s in subs
        ],
        page=page,
        limit=limit,
        total=total,
    )


@app.get("/leaderboard", response_model=list[LeaderboardEntry])
def leaderboard(page: int = 1, limit: int = 20, db: Session = Depends(get_db), user=Depends(get_current_user)):
    limit = min(limit, 100)
    offset = (page - 1) * limit

    rows = (
        db.query(
            SubmissionDB.user_id,
            UserDB.name,
            func.sum(SubmissionDB.score).label("total_score"),
            func.count(SubmissionDB.id).label("submissions"),
            func.avg(SubmissionDB.percentage).label("average_percentage"),
        )
        .join(UserDB, SubmissionDB.user_id == UserDB.id)
        .group_by(SubmissionDB.user_id, UserDB.name)
        .order_by(func.sum(SubmissionDB.score).desc(), func.avg(SubmissionDB.percentage).desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        LeaderboardEntry(
            user_id=r.user_id,
            name=r.name,
            total_score=r.total_score or 0,
            submissions=r.submissions or 0,
            average_percentage=round(float(r.average_percentage or 0), 1),
        )
        for r in rows
    ]


@app.get("/quizzes/{quiz_id}/leaderboard", response_model=list[QuizLeaderboardEntry])
def quiz_leaderboard(quiz_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    quiz = db.query(QuizDB).filter(QuizDB.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz não encontrado")

    rows = (
        db.query(
            SubmissionDB.user_id,
            UserDB.name,
            SubmissionDB.score,
            SubmissionDB.max_score,
            SubmissionDB.percentage,
        )
        .join(UserDB, SubmissionDB.user_id == UserDB.id)
        .filter(SubmissionDB.quiz_id == quiz_id)
        .order_by(SubmissionDB.percentage.desc(), SubmissionDB.score.desc())
        .limit(20)
        .all()
    )

    return [
        QuizLeaderboardEntry(
            user_id=r.user_id,
            name=r.name,
            score=r.score,
            max_score=r.max_score,
            percentage=r.percentage,
        )
        for r in rows
    ]


@app.get("/users/{user_id}/profile", response_model=PublicProfileResponse)
def public_profile(user_id: int, db: Session = Depends(get_db)):
    target = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    quizzes_created = db.query(QuizDB).filter(QuizDB.user_id == user_id).count()

    sub_stats = db.query(
        func.coalesce(func.count(SubmissionDB.id), 0),
        func.coalesce(func.avg(SubmissionDB.percentage), 0.0),
        func.coalesce(func.max(SubmissionDB.percentage), 0),
    ).filter(SubmissionDB.user_id == user_id).first()

    sub_count = sub_stats[0] or 0
    avg_val = sub_stats[1] or 0.0
    avg_score = round(float(avg_val), 1) if sub_count > 0 else 0.0
    best_score = sub_stats[2] or 0

    has_perfect = db.query(SubmissionDB).filter(
        SubmissionDB.user_id == user_id,
        SubmissionDB.percentage == 100,
    ).first() is not None

    badges = []
    if sub_count >= 1:
        badges.append(Badge(name="Primeiro Quiz Respondido", icon="🎯", description="Primeira submissão"))
    if sub_count >= 10:
        badges.append(Badge(name="Quizzeiro", icon="🏅", description="10 submissões"))
    if sub_count >= 50:
        badges.append(Badge(name="Veterano", icon="🏆", description="50 submissões"))
    if has_perfect:
        badges.append(Badge(name="Perfeccionista", icon="💯", description="100% em um quiz"))
    if quizzes_created >= 1:
        badges.append(Badge(name="Criador", icon="✍️", description="Criou um quiz"))

    user_quizzes = db.query(QuizDB).filter(QuizDB.user_id == user_id).order_by(QuizDB.created_at.desc()).all()
    total_views = db.query(func.coalesce(func.sum(QuizDB.views), 0)).filter(QuizDB.user_id == user_id).scalar() or 0
    ranking_pos = _ranking_position(user_id, db)

    return PublicProfileResponse(
        id=target.id,
        name=target.name,
        role=target.role,
        quizzes_created=quizzes_created,
        submissions=sub_count,
        average_score=avg_score,
        best_score=best_score,
        total_views=total_views,
        ranking_position=ranking_pos,
        badges=badges,
        quizzes=[{"id": q.id, "title": q.title, "views": q.views or 0, "created_at": q.created_at.isoformat() if q.created_at else None} for q in user_quizzes],
    )


def _ranking_position(user_id: int, db: Session) -> int:
    user_total = db.query(
        func.coalesce(func.sum(SubmissionDB.score), 0)
    ).filter(SubmissionDB.user_id == user_id).scalar()

    if user_total == 0:
        return 0

    subq = (
        db.query(
            SubmissionDB.user_id,
            func.sum(SubmissionDB.score).label("total_score"),
        )
        .group_by(SubmissionDB.user_id)
        .subquery()
    )
    above = (
        db.query(func.count())
        .select_from(subq)
        .filter(subq.c.total_score > user_total)
        .scalar()
    )
    return above + 1


@app.get("/categories", response_model=list[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return db.query(CategoryDB).order_by(CategoryDB.name).all()


@app.get("/tags", response_model=list[TagResponse])
def list_tags(db: Session = Depends(get_db)):
    return db.query(TagDB).order_by(TagDB.name).all()


@app.get("/me/dashboard", response_model=DashboardResponse)
def dashboard(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    quizzes_created = db.query(QuizDB).filter(QuizDB.user_id == user.id).count()

    sub_stats = db.query(
        func.count(SubmissionDB.id),
        func.count(func.distinct(SubmissionDB.quiz_id)),
        func.coalesce(func.sum(SubmissionDB.score), 0),
        func.coalesce(func.max(SubmissionDB.percentage), 0),
        func.coalesce(func.avg(SubmissionDB.percentage), 0.0),
    ).filter(SubmissionDB.user_id == user.id).first()

    total_submissions = sub_stats[0] or 0
    total_quizzes_responded = sub_stats[1] or 0
    total_answers_submitted = sub_stats[2] or 0
    best_percentage = sub_stats[3] or 0
    avg_val = sub_stats[4] or 0.0
    average_percentage = round(float(avg_val), 1) if total_submissions > 0 else 0.0

    ranking_position = _ranking_position(user.id, db)

    total_views = db.query(
        func.coalesce(func.sum(QuizDB.views), 0)
    ).filter(QuizDB.user_id == user.id).scalar() or 0

    most_viewed = (
        db.query(QuizDB)
        .filter(QuizDB.user_id == user.id)
        .order_by(QuizDB.views.desc())
        .first()
    )
    most_viewed_quiz = {"id": most_viewed.id, "title": most_viewed.title, "views": most_viewed.views} if most_viewed else None

    recent_quizzes = (
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
        best_percentage=best_percentage,
        average_percentage=average_percentage,
        ranking_position=ranking_position,
        total_views=total_views,
        most_viewed_quiz=most_viewed_quiz,
        recent_quizzes=[RecentQuizItem(id=q.id, title=q.title, created_at=q.created_at) for q in recent_quizzes],
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
def health(db: Session = Depends(get_db)):
    db_status = "healthy"
    db_type = "sqlite" if "sqlite" in str(db.bind.url) else "postgresql"
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"
    return {
        "status": "healthy",
        "database": db_status,
        "database_type": db_type,
        "version": APP_VERSION,
        "uptime_seconds": round(time.time() - _app_start_time),
        "environment": ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


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


@app.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    total_users = db.query(UserDB).count()
    total_quizzes = db.query(QuizDB).count()
    total_submissions = db.query(SubmissionDB).count()
    db_type = "sqlite" if "sqlite" in str(db.bind.url) else "postgresql"
    return {
        "uptime_seconds": round(time.time() - _app_start_time),
        "total_users": total_users,
        "total_quizzes": total_quizzes,
        "total_submissions": total_submissions,
        "database": db_type,
        "version": APP_VERSION,
    }


@app.get("/admin/dashboard", response_model=AdminDashboardResponse)
def admin_dashboard(
    user: UserDB = Depends(require_admin),
    db: Session = Depends(get_db),
):
    total_users = db.query(UserDB).count()
    total_admins = db.query(UserDB).filter(UserDB.role == "admin").count()
    total_quizzes = db.query(QuizDB).count()
    total_submissions = db.query(SubmissionDB).count()

    users_list = db.query(UserDB).order_by(UserDB.created_at.desc()).all()

    quiz_counts = dict(
        db.query(QuizDB.user_id, func.count(QuizDB.id))
        .group_by(QuizDB.user_id)
        .all()
    )
    sub_counts = dict(
        db.query(SubmissionDB.user_id, func.count(SubmissionDB.id))
        .group_by(SubmissionDB.user_id)
        .all()
    )

    users_data = []
    for u in users_list:
        users_data.append(AdminUserItem(
            id=u.id, name=u.name, email=u.email, role=u.role,
            created_at=u.created_at,
            quizzes_count=quiz_counts.get(u.id, 0),
            submissions_count=sub_counts.get(u.id, 0),
        ))

    return AdminDashboardResponse(
        total_users=total_users,
        total_admins=total_admins,
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

    quiz_counts = dict(
        db.query(QuizDB.user_id, func.count(QuizDB.id))
        .group_by(QuizDB.user_id)
        .all()
    )
    sub_counts = dict(
        db.query(SubmissionDB.user_id, func.count(SubmissionDB.id))
        .group_by(SubmissionDB.user_id)
        .all()
    )

    result = []
    for u in users_list:
        result.append(AdminUserItem(
            id=u.id, name=u.name, email=u.email, role=u.role,
            created_at=u.created_at,
            quizzes_count=quiz_counts.get(u.id, 0),
            submissions_count=sub_counts.get(u.id, 0),
        ))
    return result


@app.put("/admin/users/{user_id}/role")
@app.patch("/admin/users/{user_id}/role")
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


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    logger.info("Servidor iniciando na porta %s", port)
    uvicorn.run("main:app", host="0.0.0.0", port=port)
