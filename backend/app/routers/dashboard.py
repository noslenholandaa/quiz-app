from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.models.database import get_db
from app.schemas.models import DashboardResponse, StatsResponse, SubmissionListResponse
from app.services import dashboard_service

router = APIRouter(tags=["dashboard"])


@router.get("/me/dashboard", response_model=DashboardResponse)
def dashboard(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return dashboard_service.get_dashboard(user, db)


@router.get("/me/stats", response_model=StatsResponse)
def stats(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return dashboard_service.get_stats(user, db)


@router.get("/me/submissions", response_model=SubmissionListResponse)
def list_my_submissions(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = 1,
    limit: int = 20,
):
    return dashboard_service.list_my_submissions(user, db, page, limit)
