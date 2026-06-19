from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.schemas.models import PublicProfileResponse
from app.services import leaderboard_service

router = APIRouter(tags=["profile"])


@router.get("/users/{user_id}/profile", response_model=PublicProfileResponse)
def public_profile(user_id: int, db: Session = Depends(get_db)):
    return leaderboard_service.get_public_profile(user_id, db)
