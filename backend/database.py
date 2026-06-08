from datetime import datetime, timezone

from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, JSON, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from config import DATABASE_URL

_connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    submissions = relationship("SubmissionDB", back_populates="owner", cascade="all, delete-orphan")
    quizzes = relationship("QuizDB", back_populates="creator", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshTokenDB", back_populates="owner", cascade="all, delete-orphan")


class SubmissionDB(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    quiz_id = Column(Integer, nullable=False)
    quiz_title = Column(String, nullable=False)
    answers = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner = relationship("UserDB", back_populates="submissions")


class QuizDB(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String, nullable=False)
    description = Column(String, default="")
    questions = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    creator = relationship("UserDB", back_populates="quizzes")


class RefreshTokenDB(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    user_agent = Column(Text, default="")
    ip_address = Column(String, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_used_at = Column(DateTime, nullable=True)

    owner = relationship("UserDB", back_populates="refresh_tokens")


def create_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


SEED_QUIZZES = [
    {
        "user_id": None,
        "title": "Pesquisa de Satisfação",
        "description": "Ajude-nos a melhorar nossos serviços respondendo a esta rápida pesquisa.",
        "questions": [
            {"id": 1, "text": "Como você avalia nosso atendimento?", "type": "rating", "required": True,
             "options": [
                 {"id": 1, "text": "1 - Péssimo"}, {"id": 2, "text": "2 - Ruim"},
                 {"id": 3, "text": "3 - Regular"}, {"id": 4, "text": "4 - Bom"},
                 {"id": 5, "text": "5 - Excelente"},
             ]},
            {"id": 2, "text": "Quais canais você utilizou? (pode selecionar mais de um)", "type": "multiple_choice", "required": True,
             "options": [
                 {"id": 1, "text": "WhatsApp"}, {"id": 2, "text": "E-mail"},
                 {"id": 3, "text": "Telefone"}, {"id": 4, "text": "Chat online"},
                 {"id": 5, "text": "Presencial"},
             ]},
            {"id": 3, "text": "Você recomendaria nossos serviços para um amigo?", "type": "single_choice", "required": True,
             "options": [
                 {"id": 1, "text": "Sim, com certeza"}, {"id": 2, "text": "Talvez"},
                 {"id": 3, "text": "Não"},
             ]},
            {"id": 4, "text": "Deixe seu comentário ou sugestão:", "type": "text", "required": False},
        ],
    },
    {
        "user_id": None,
        "title": "Quiz de Conhecimentos Gerais",
        "description": "Teste seus conhecimentos com este quiz rápido!",
        "questions": [
            {"id": 1, "text": "Qual a capital do Brasil?", "type": "single_choice", "required": True,
             "options": [
                 {"id": 1, "text": "Rio de Janeiro"}, {"id": 2, "text": "São Paulo"},
                 {"id": 3, "text": "Brasília"}, {"id": 4, "text": "Salvador"},
             ]},
            {"id": 2, "text": "Quais destes são linguagens de programação? (marque todos)", "type": "multiple_choice", "required": True,
             "options": [
                 {"id": 1, "text": "Python"}, {"id": 2, "text": "HTML"},
                 {"id": 3, "text": "JavaScript"}, {"id": 4, "text": "CSS"},
                 {"id": 5, "text": "Cobra"},
             ]},
            {"id": 3, "text": "Em que ano o homem pisou na Lua pela primeira vez?", "type": "text", "required": True},
        ],
    },
]


def seed_quizzes(db):
    existing = db.query(QuizDB).count()
    if existing > 0:
        return
    for data in SEED_QUIZZES:
        db.add(QuizDB(**data))
    db.commit()
    from sqlalchemy import text
    dialect = db.bind.dialect.name
    if dialect == "postgresql":
        max_id = db.query(db.query(QuizDB).order_by(QuizDB.id.desc()).limit(1).subquery().c.id).scalar()
        if max_id:
            db.execute(text(f"SELECT setval('quizzes_id_seq', {max_id})"))
