import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.database import UserDB, QuizDB, SubmissionDB
from app.schemas.models import AdminDashboardResponse, AdminUserItem, SetRoleInput

logger = logging.getLogger("quizapp")


def get_admin_dashboard(db: Session) -> AdminDashboardResponse:
    total_users = db.query(UserDB).count()
    total_admins = db.query(UserDB).filter(UserDB.role == "admin").count()
    total_quizzes = db.query(QuizDB).count()
    total_submissions = db.query(SubmissionDB).count()

    users_list = db.query(UserDB).order_by(UserDB.created_at.desc()).all()

    quiz_counts = dict(
        db.query(QuizDB.user_id, func.count(QuizDB.id))
        .group_by(QuizDB.user_id)
        .all()
    )
    sub_counts = dict(
        db.query(SubmissionDB.user_id, func.count(SubmissionDB.id))
        .group_by(SubmissionDB.user_id)
        .all()
    )

    users_data = []
    for u in users_list:
        users_data.append(AdminUserItem(
            id=u.id, name=u.name, email=u.email, role=u.role,
            created_at=u.created_at,
            quizzes_count=quiz_counts.get(u.id, 0),
            submissions_count=sub_counts.get(u.id, 0),
        ))

    return AdminDashboardResponse(
        total_users=total_users,
        total_admins=total_admins,
        total_quizzes=total_quizzes,
        total_submissions=total_submissions,
        users=users_data,
    )


def list_admin_users(db: Session) -> list[AdminUserItem]:
    users_list = db.query(UserDB).order_by(UserDB.created_at.desc()).all()

    quiz_counts = dict(
        db.query(QuizDB.user_id, func.count(QuizDB.id))
        .group_by(QuizDB.user_id)
        .all()
    )
    sub_counts = dict(
        db.query(SubmissionDB.user_id, func.count(SubmissionDB.id))
        .group_by(SubmissionDB.user_id)
        .all()
    )

    result = []
    for u in users_list:
        result.append(AdminUserItem(
            id=u.id, name=u.name, email=u.email, role=u.role,
            created_at=u.created_at,
            quizzes_count=quiz_counts.get(u.id, 0),
            submissions_count=sub_counts.get(u.id, 0),
        ))
    return result


def set_user_role(user_id: int, body: SetRoleInput, admin_user: UserDB, db: Session) -> dict:
    target = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    new_role = body.role
    if new_role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Role deve ser 'admin' ou 'user'")
    if target.id == admin_user.id:
        raise HTTPException(status_code=400, detail="Você não pode alterar seu próprio role")
    target.role = new_role
    db.commit()
    logger.info("Admin %s alterou role do usuario %s para %s", admin_user.id, user_id, new_role)
    return {"detail": f"Role atualizado para {new_role}"}
