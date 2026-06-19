from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.database import QuizDB, SubmissionDB, UserDB
from app.schemas.models import (
    LeaderboardEntry, QuizLeaderboardEntry, PublicProfileResponse, Badge,
)


def get_leaderboard(db: Session, page: int = 1, limit: int = 20) -> list[LeaderboardEntry]:
    limit = min(limit, 100)
    offset = (page - 1) * limit

    rows = (
        db.query(
            SubmissionDB.user_id,
            UserDB.name,
            func.sum(SubmissionDB.score).label("total_score"),
            func.count(SubmissionDB.id).label("submissions"),
            func.avg(SubmissionDB.percentage).label("average_percentage"),
        )
        .join(UserDB, SubmissionDB.user_id == UserDB.id)
        .group_by(SubmissionDB.user_id, UserDB.name)
        .order_by(func.sum(SubmissionDB.score).desc(), func.avg(SubmissionDB.percentage).desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        LeaderboardEntry(
            user_id=r.user_id,
            name=r.name,
            total_score=r.total_score or 0,
            submissions=r.submissions or 0,
            average_percentage=round(float(r.average_percentage or 0), 1),
        )
        for r in rows
    ]


def get_quiz_leaderboard(quiz_id: int, db: Session) -> list[QuizLeaderboardEntry]:
    quiz = db.query(QuizDB).filter(QuizDB.id == quiz_id).first()
    if not quiz:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Quiz não encontrado")

    rows = (
        db.query(
            SubmissionDB.user_id,
            UserDB.name,
            SubmissionDB.score,
            SubmissionDB.max_score,
            SubmissionDB.percentage,
        )
        .join(UserDB, SubmissionDB.user_id == UserDB.id)
        .filter(SubmissionDB.quiz_id == quiz_id)
        .order_by(SubmissionDB.percentage.desc(), SubmissionDB.score.desc())
        .limit(20)
        .all()
    )

    return [
        QuizLeaderboardEntry(
            user_id=r.user_id,
            name=r.name,
            score=r.score,
            max_score=r.max_score,
            percentage=r.percentage,
        )
        for r in rows
    ]


def get_public_profile(user_id: int, db: Session) -> PublicProfileResponse:
    target = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not target:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    quizzes_created = db.query(QuizDB).filter(QuizDB.user_id == user_id).count()

    sub_stats = db.query(
        func.coalesce(func.count(SubmissionDB.id), 0),
        func.coalesce(func.avg(SubmissionDB.percentage), 0.0),
        func.coalesce(func.max(SubmissionDB.percentage), 0),
    ).filter(SubmissionDB.user_id == user_id).first()

    sub_count = sub_stats[0] or 0
    avg_val = sub_stats[1] or 0.0
    avg_score = round(float(avg_val), 1) if sub_count > 0 else 0.0
    best_score = sub_stats[2] or 0

    has_perfect = db.query(SubmissionDB).filter(
        SubmissionDB.user_id == user_id,
        SubmissionDB.percentage == 100,
    ).first() is not None

    badges = []
    if sub_count >= 1:
        badges.append(Badge(name="Primeiro Quiz Respondido", icon="🎯", description="Primeira submissão"))
    if sub_count >= 10:
        badges.append(Badge(name="Quizzeiro", icon="🏅", description="10 submissões"))
    if sub_count >= 50:
        badges.append(Badge(name="Veterano", icon="🏆", description="50 submissões"))
    if has_perfect:
        badges.append(Badge(name="Perfeccionista", icon="💯", description="100% em um quiz"))
    if quizzes_created >= 1:
        badges.append(Badge(name="Criador", icon="✍️", description="Criou um quiz"))

    user_quizzes = db.query(QuizDB).filter(QuizDB.user_id == user_id).order_by(QuizDB.created_at.desc()).all()
    total_views = db.query(func.coalesce(func.sum(QuizDB.views), 0)).filter(QuizDB.user_id == user_id).scalar() or 0
    ranking_pos = _ranking_position(user_id, db)

    return PublicProfileResponse(
        id=target.id,
        name=target.name,
        role=target.role,
        quizzes_created=quizzes_created,
        submissions=sub_count,
        average_score=avg_score,
        best_score=best_score,
        total_views=total_views,
        ranking_position=ranking_pos,
        badges=badges,
        quizzes=[{"id": q.id, "title": q.title, "views": q.views or 0, "created_at": q.created_at.isoformat() if q.created_at else None} for q in user_quizzes],
    )


def _ranking_position(user_id: int, db: Session) -> int:
    user_total = db.query(
        func.coalesce(func.sum(SubmissionDB.score), 0)
    ).filter(SubmissionDB.user_id == user_id).scalar()

    if user_total == 0:
        return 0

    subq = (
        db.query(
            SubmissionDB.user_id,
            func.sum(SubmissionDB.score).label("total_score"),
        )
        .group_by(SubmissionDB.user_id)
        .subquery()
    )
    above = (
        db.query(func.count())
        .select_from(subq)
        .filter(subq.c.total_score > user_total)
        .scalar()
    )
    return above + 1
