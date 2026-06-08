import os


SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-mude-em-producao")
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY", "super-refresh-secret-mude-em-producao")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./quiz.db")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
RATE_LIMIT_LOGIN_PER_MINUTE = int(os.getenv("RATE_LIMIT_LOGIN_PER_MINUTE", "10"))
RATE_LIMIT_REGISTER_PER_HOUR = int(os.getenv("RATE_LIMIT_REGISTER_PER_HOUR", "5"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "text").lower()
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
