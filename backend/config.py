import os


ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-mude-em-producao")
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY", "super-refresh-secret-mude-em-producao")

_DEFAULT_SECRET = "super-secret-key-mude-em-producao"
_DEFAULT_REFRESH_SECRET = "super-refresh-secret-mude-em-producao"

if ENVIRONMENT == "production":
    if not SECRET_KEY or SECRET_KEY == _DEFAULT_SECRET:
        raise RuntimeError(
            "SECRET_KEY invalida ou ausente em producao. "
            "Defina SECRET_KEY como uma string aleatoria segura."
        )
    if not REFRESH_SECRET_KEY or REFRESH_SECRET_KEY == _DEFAULT_REFRESH_SECRET:
        raise RuntimeError(
            "REFRESH_SECRET_KEY invalida ou ausente em producao. "
            "Defina REFRESH_SECRET_KEY como uma string aleatoria segura."
        )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./quiz.db")

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
if ENVIRONMENT == "production" and CORS_ORIGINS == ["*"]:
    raise RuntimeError(
        "CORS_ORIGINS nao pode ser '*' em producao. "
        "Defina CORS_ORIGINS como a URL do frontend."
    )

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*" if ENVIRONMENT != "production" else "").split(",")
if ENVIRONMENT == "production" and (not ALLOWED_HOSTS or ALLOWED_HOSTS == [""] or ALLOWED_HOSTS == ["*"]):
    raise RuntimeError(
        "ALLOWED_HOSTS obrigatorio em producao. "
        "Exemplo: ALLOWED_HOSTS=quiz-app.onrender.com,localhost,127.0.0.1"
    )

RATE_LIMIT_LOGIN_PER_MINUTE = int(os.getenv("RATE_LIMIT_LOGIN_PER_MINUTE", "10"))
RATE_LIMIT_REGISTER_PER_HOUR = int(os.getenv("RATE_LIMIT_REGISTER_PER_HOUR", "5"))
ADMIN_EMAILS = os.getenv("ADMIN_EMAILS", "noslenalan@gmail.com").lower().split(",")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "text").lower()

# SMTP — para envio real de emails (ex: recuperação de senha)
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@quizapp.com")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
SMTP_TIMEOUT = int(os.getenv("SMTP_TIMEOUT", "30"))

APP_VERSION = "1.2.0"
