from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.models.database import get_db, UserDB
from app.schemas.models import AdminDashboardResponse, AdminUserItem, SetRoleInput
from app.services import admin_service

router = APIRouter(tags=["admin"])


@router.get("/admin/dashboard", response_model=AdminDashboardResponse)
def admin_dashboard(
    user: UserDB = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return admin_service.get_admin_dashboard(db)


@router.get("/admin/users", response_model=list[AdminUserItem])
def admin_list_users(
    user: UserDB = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return admin_service.list_admin_users(db)


@router.put("/admin/users/{user_id}/role")
@router.patch("/admin/users/{user_id}/role")
def admin_set_role(
    user_id: int,
    body: SetRoleInput,
    user: UserDB = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return admin_service.set_user_role(user_id, body, user, db)
