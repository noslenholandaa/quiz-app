import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import APP_VERSION, ENVIRONMENT
from app.models.database import get_db, UserDB, QuizDB, SubmissionDB

_app_start_time: float = time.time()

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db_status = "healthy"
    db_type = "sqlite" if "sqlite" in str(db.bind.url) else "postgresql"
    try:
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


@router.get("/health/database")
def health_database(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        url_str = str(db.bind.url) if db.bind.url else "unknown"
        if "@" in url_str:
            url_str = url_str.split("@", 1)[0].split("://", 1)[0] + "://<redacted>@" + url_str.split("@", 1)[1]
        return {"status": "healthy", "database": url_str}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")


@router.get("/metrics")
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
