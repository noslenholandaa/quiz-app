import os


SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-mude-em-producao")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./quiz.db")
