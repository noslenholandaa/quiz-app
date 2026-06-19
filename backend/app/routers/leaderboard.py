from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.models.database import get_db
from app.schemas.models import LeaderboardEntry, QuizLeaderboardEntry
from app.services import leaderboard_service

router = APIRouter(tags=["leaderboard"])


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
def leaderboard(page: int = 1, limit: int = 20, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return leaderboard_service.get_leaderboard(db, page, limit)


@router.get("/quizzes/{quiz_id}/leaderboard", response_model=list[QuizLeaderboardEntry])
def quiz_leaderboard(quiz_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return leaderboard_service.get_quiz_leaderboard(quiz_id, db)
