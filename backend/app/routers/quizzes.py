import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_admin
from app.models.database import get_db
from app.schemas.models import (
    Quiz, QuizCreate, QuizUpdate, SubmissionInput, SubmissionResponse,
    SearchResult,
)
from app.services import quiz_service

logger = logging.getLogger("quizapp")
router = APIRouter(tags=["quizzes"])


@router.get("/quizzes", response_model=list[Quiz])
def list_quizzes(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return quiz_service.list_quizzes(user, db)


@router.get("/quizzes/search", response_model=SearchResult)
def search_quizzes(
    q: str = "",
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return quiz_service.search_quizzes(q, page, limit, user, db)


@router.get("/quizzes/{quiz_id}", response_model=Quiz)
def get_quiz(quiz_id: int, db: Session = Depends(get_db)):
    return quiz_service.get_quiz(quiz_id, db)


@router.post("/quizzes", response_model=Quiz, status_code=201)
def create_quiz(
    data: QuizCreate,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return quiz_service.create_quiz(data, user, db)


@router.put("/quizzes/{quiz_id}", response_model=Quiz)
def update_quiz(
    quiz_id: int,
    data: QuizUpdate,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return quiz_service.update_quiz(quiz_id, data, user, db)


@router.delete("/quizzes/{quiz_id}", status_code=204)
def delete_quiz(
    quiz_id: int,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    quiz_service.delete_quiz(quiz_id, user, db)


@router.get("/me/quizzes", response_model=list[Quiz])
def list_my_quizzes(
    user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return quiz_service.list_my_quizzes(user, db)


@router.post("/quizzes/{quiz_id}/submit", response_model=SubmissionResponse)
def submit_quiz(
    quiz_id: int,
    submission: SubmissionInput,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return quiz_service.submit_quiz(quiz_id, submission, user, db)
