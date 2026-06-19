import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

logger = logging.getLogger("quizapp")
from sqlalchemy import func

from app.models.database import QuizDB, SubmissionDB, UserDB
from app.services.quiz_service import _get_answer_text, _is_correct
from app.schemas.models import (
    DashboardResponse, RecentQuizItem, RecentSubmissionItem,
    StatsResponse, PeriodStats,
    SubmissionListResponse, SubmissionResponse, AnswerResponse,
)


def get_dashboard(user: UserDB, db: Session) -> DashboardResponse:
    quizzes_created = db.query(QuizDB).filter(QuizDB.user_id == user.id).count()

    sub_stats = db.query(
        func.count(SubmissionDB.id),
        func.count(func.distinct(SubmissionDB.quiz_id)),
        func.coalesce(func.sum(SubmissionDB.score), 0),
        func.coalesce(func.max(SubmissionDB.percentage), 0),
        func.coalesce(func.avg(SubmissionDB.percentage), 0.0),
    ).filter(SubmissionDB.user_id == user.id).first()

    total_submissions = sub_stats[0] or 0
    total_quizzes_responded = sub_stats[1] or 0
    total_answers_submitted = sub_stats[2] or 0
    best_percentage = sub_stats[3] or 0
    avg_val = sub_stats[4] or 0.0
    average_percentage = round(float(avg_val), 1) if total_submissions > 0 else 0.0

    ranking_position = _ranking_position(user.id, db)

    total_views = db.query(
        func.coalesce(func.sum(QuizDB.views), 0)
    ).filter(QuizDB.user_id == user.id).scalar() or 0

    most_viewed = (
        db.query(QuizDB)
        .filter(QuizDB.user_id == user.id)
        .order_by(QuizDB.views.desc())
        .first()
    )
    most_viewed_quiz = {"id": most_viewed.id, "title": most_viewed.title, "views": most_viewed.views} if most_viewed else None

    recent_quizzes = (
        db.query(QuizDB)
        .filter(QuizDB.user_id == user.id)
        .order_by(QuizDB.created_at.desc())
        .limit(5)
        .all()
    )
    recent_subs = (
        db.query(SubmissionDB)
        .filter(SubmissionDB.user_id == user.id)
        .order_by(SubmissionDB.created_at.desc())
        .limit(5)
        .all()
    )

    return DashboardResponse(
        total_quizzes_created=quizzes_created,
        total_quizzes_responded=total_quizzes_responded,
        total_submissions=total_submissions,
        total_answers_submitted=total_answers_submitted,
        best_percentage=best_percentage,
        average_percentage=average_percentage,
        ranking_position=ranking_position,
        total_views=total_views,
        most_viewed_quiz=most_viewed_quiz,
        recent_quizzes=[RecentQuizItem(id=q.id, title=q.title, created_at=q.created_at) for q in recent_quizzes],
        recent_submissions=[RecentSubmissionItem(id=s.id, quiz_id=s.quiz_id, quiz_title=s.quiz_title, created_at=s.created_at) for s in recent_subs],
    )


def get_stats(user: UserDB, db: Session) -> StatsResponse:
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    subs_7 = db.query(SubmissionDB).filter(
        SubmissionDB.user_id == user.id,
        SubmissionDB.created_at >= seven_days_ago,
    ).count()
    subs_30 = db.query(SubmissionDB).filter(
        SubmissionDB.user_id == user.id,
        SubmissionDB.created_at >= thirty_days_ago,
    ).count()

    qz_7 = db.query(QuizDB).filter(
        QuizDB.user_id == user.id,
        QuizDB.created_at >= seven_days_ago,
    ).count()
    qz_30 = db.query(QuizDB).filter(
        QuizDB.user_id == user.id,
        QuizDB.created_at >= thirty_days_ago,
    ).count()

    return StatsResponse(
        last_7_days=PeriodStats(submissions=subs_7, quizzes_created=qz_7),
        last_30_days=PeriodStats(submissions=subs_30, quizzes_created=qz_30),
    )


def _enrich_answer(a: dict, quiz_questions: dict) -> dict:
    q = quiz_questions.get(a.get("question_id"))
    if not q:
        return a
    enriched = dict(a)
    if "correct" not in enriched:
        enriched["correct"] = _is_correct(q, a["answer"])
    if not enriched.get("answer_text"):
        enriched["answer_text"] = _get_answer_text(q, a["answer"])
    return enriched


def list_my_submissions(user: UserDB, db: Session, page: int = 1, limit: int = 20) -> SubmissionListResponse:
    limit = min(limit, 100)
    offset = (page - 1) * limit
    base = db.query(SubmissionDB).filter(SubmissionDB.user_id == user.id)
    total = base.count()
    subs = base.order_by(SubmissionDB.created_at.desc()).offset(offset).limit(limit).all()

    items = []
    for s in subs:
        quiz = db.query(QuizDB).filter(QuizDB.id == s.quiz_id).first()
        quiz_questions = {q["id"]: q for q in quiz.questions} if quiz else {}
        enriched_answers = [_enrich_answer(a, quiz_questions) for a in s.answers]
        correct_count = sum(1 for a in enriched_answers if a.get("correct"))
        ans_total = len(enriched_answers)
        recalculated_score = correct_count
        recalculated_max = ans_total
        recalculated_pct = round((correct_count / ans_total) * 100) if ans_total > 0 else 0
        logger.debug(
            "Submission %s: DB(score=%s max=%s pct=%s) enriched(correct=%s/%s) => recalc(score=%s pct=%s)",
            s.id, s.score, s.max_score, s.percentage,
            correct_count, ans_total, recalculated_score, recalculated_pct,
        )
        items.append(SubmissionResponse(
            id=s.id,
            user_id=s.user_id,
            quiz_id=s.quiz_id,
            quiz_title=s.quiz_title,
            answers=[AnswerResponse(**a) for a in enriched_answers],
            score=recalculated_score,
            max_score=recalculated_max,
            percentage=recalculated_pct,
            created_at=s.created_at,
        ))

    return SubmissionListResponse(
        items=items,
        page=page,
        limit=limit,
        total=total,
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
