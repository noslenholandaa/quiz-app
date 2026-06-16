from datetime import datetime, timezone

from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, JSON, Text, Boolean, Index, Table
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
    __table_args__ = (
        Index("ix_users_role", "role"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    submissions = relationship("SubmissionDB", back_populates="owner", cascade="all, delete-orphan")
    quizzes = relationship("QuizDB", back_populates="creator", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshTokenDB", back_populates="owner", cascade="all, delete-orphan")


class SubmissionDB(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    quiz_title = Column(String, nullable=False)
    answers = Column(JSON, nullable=False)
    score = Column(Integer, default=0)
    max_score = Column(Integer, default=0)
    percentage = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner = relationship("UserDB", back_populates="submissions")

    __table_args__ = (
        Index("ix_submissions_user_id", "user_id"),
        Index("ix_submissions_quiz_id", "quiz_id"),
        Index("ix_submissions_created_at", "created_at"),
        Index("ix_submissions_percentage", "percentage"),
    )


class CategoryDB(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    quizzes = relationship("QuizDB", back_populates="category")


class TagDB(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class QuizDB(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    title = Column(String, nullable=False)
    description = Column(String, default="")
    questions = Column(JSON, nullable=False)
    views = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    creator = relationship("UserDB", back_populates="quizzes")
    category = relationship("CategoryDB", back_populates="quizzes")

    __table_args__ = (
        Index("ix_quizzes_title", "title"),
        Index("ix_quizzes_category_id", "category_id"),
        Index("ix_quizzes_views", "views"),
        Index("ix_quizzes_created_at", "created_at"),
    )


quiz_tags = Table(
    "quiz_tags", Base.metadata,
    Column("quiz_id", Integer, ForeignKey("quizzes.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)

QuizDB.tags = relationship("TagDB", secondary=quiz_tags, back_populates="quizzes")
TagDB.quizzes = relationship("QuizDB", secondary=quiz_tags, back_populates="tags")


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

    __table_args__ = (
        Index("ix_refresh_tokens_expires_at", "expires_at"),
    )


class PasswordResetTokenDB(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_password_reset_tokens_expires_at", "expires_at"),
    )


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
    {
        "user_id": None,
        "title": "Pesquisa de Estilo de Vida",
        "description": "Conte-nos sobre seus hábitos e preferências para ajudarmos a criar conteúdo relevante.",
        "questions": [
            {"id": 1, "text": "Quais atividades você pratica regularmente? (marque todas que se aplicam)", "type": "multiple_choice", "required": True,
             "options": [
                 {"id": 1, "text": "Atividades físicas"}, {"id": 2, "text": "Leitura"},
                 {"id": 3, "text": "Jogos"}, {"id": 4, "text": "Música"},
                 {"id": 5, "text": "Viagens"}, {"id": 6, "text": "Culinária"},
                 {"id": 7, "text": "Voluntariado"},
             ]},
            {"id": 2, "text": "Quantas horas por dia você passa em frente a telas?", "type": "single_choice", "required": True,
             "options": [
                 {"id": 1, "text": "Menos de 2h"}, {"id": 2, "text": "2h a 4h"},
                 {"id": 3, "text": "4h a 8h"}, {"id": 4, "text": "Mais de 8h"},
             ]},
            {"id": 3, "text": "Como você avalia sua qualidade de sono?", "type": "rating", "required": True,
             "options": [
                 {"id": 1, "text": "1 - Péssima"}, {"id": 2, "text": "2 - Ruim"},
                 {"id": 3, "text": "3 - Regular"}, {"id": 4, "text": "4 - Boa"},
                 {"id": 5, "text": "5 - Excelente"},
             ]},
            {"id": 4, "text": "Qual seu maior hobby atualmente?", "type": "text", "required": False},
            {"id": 5, "text": "Você se considera mais produtivo pela manhã ou à noite?", "type": "single_choice", "required": True,
             "options": [
                 {"id": 1, "text": "Manhã"}, {"id": 2, "text": "Tarde"},
                 {"id": 3, "text": "Noite"}, {"id": 4, "text": "Madrugada"},
             ]},
            {"id": 6, "text": "Quais redes sociais você mais usa? (pode escolher mais de uma)", "type": "multiple_choice", "required": True,
             "options": [
                 {"id": 1, "text": "Instagram"}, {"id": 2, "text": "YouTube"},
                 {"id": 3, "text": "Twitter/X"}, {"id": 4, "text": "LinkedIn"},
                 {"id": 5, "text": "TikTok"}, {"id": 6, "text": "WhatsApp"},
             ]},
            {"id": 7, "text": "Deixe uma dica de hábito saudável que funciona para você:", "type": "text", "required": False},
        ],
    },
    {
        "user_id": None,
        "title": "Quiz de Tecnologia",
        "description": "Descubra o quanto você sabe sobre o mundo da tecnologia!",
        "questions": [
            {"id": 1, "text": "Qual empresa desenvolveu o sistema operacional Android?", "type": "single_choice", "required": True,
             "options": [
                 {"id": 1, "text": "Apple"}, {"id": 2, "text": "Google"},
                 {"id": 3, "text": "Microsoft"}, {"id": 4, "text": "Samsung"},
             ]},
            {"id": 2, "text": "Quais destas são linguagens compiladas? (marque todas)", "type": "multiple_choice", "required": True,
             "options": [
                 {"id": 1, "text": "C"}, {"id": 2, "text": "Rust"},
                 {"id": 3, "text": "Python"}, {"id": 4, "text": "Java"},
                 {"id": 5, "text": "Go"}, {"id": 6, "text": "JavaScript"},
             ]},
            {"id": 3, "text": "O que significa a sigla API?", "type": "single_choice", "required": True,
             "options": [
                 {"id": 1, "text": "Application Programming Interface"}, {"id": 2, "text": "Automated Program Integration"},
                 {"id": 3, "text": "Advanced Platform Interface"}, {"id": 4, "text": "Application Process Integration"},
             ]},
            {"id": 4, "text": "Explique com suas palavras o que é computação em nuvem:", "type": "text", "required": False},
            {"id": 5, "text": "Qual banco de dados é conhecido por ser relacional?", "type": "single_choice", "required": True,
             "options": [
                 {"id": 1, "text": "MongoDB"}, {"id": 2, "text": "PostgreSQL"},
                 {"id": 3, "text": "Redis"}, {"id": 4, "text": "Firebase"},
             ]},
            {"id": 6, "text": "Quais destes são protocolos de comunicação web? (marque todos)", "type": "multiple_choice", "required": True,
             "options": [
                 {"id": 1, "text": "HTTP"}, {"id": 2, "text": "FTP"},
                 {"id": 3, "text": "SQL"}, {"id": 4, "text": "WebSocket"},
                 {"id": 5, "text": "SMTP"}, {"id": 6, "text": "JSON"},
             ]},
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
