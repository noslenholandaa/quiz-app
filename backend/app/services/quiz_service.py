import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_

from app.models.database import QuizDB, SubmissionDB, CategoryDB, TagDB, UserDB
from app.schemas.models import (
    Quiz, QuizCreate, QuizUpdate, QuestionType,
    SubmissionInput, SubmissionResponse, AnswerResponse,
    SearchResult, CategoryResponse, TagResponse,
)

logger = logging.getLogger("quizapp")


def quiz_to_response(q: QuizDB) -> Quiz:
    category = CategoryResponse.model_validate(q.category) if q.category else None
    tags = [TagResponse.model_validate(t) for t in q.tags] if q.tags else []
    return Quiz(
        id=q.id, title=q.title, description=q.description,
        questions=q.questions, category=category, tags=tags, views=q.views,
    )


def list_quizzes(user: UserDB, db: Session) -> list[Quiz]:
    mine = db.query(QuizDB).options(selectinload(QuizDB.category), selectinload(QuizDB.tags)).filter(QuizDB.user_id == user.id).all()
    public = db.query(QuizDB).options(selectinload(QuizDB.category), selectinload(QuizDB.tags)).filter(QuizDB.user_id.is_(None)).all()
    seen = set()
    result = []
    for q in public + mine:
        if q.id not in seen:
            seen.add(q.id)
            result.append(quiz_to_response(q))
    return result


def search_quizzes(q: str, page: int, limit: int, user: UserDB, db: Session) -> SearchResult:
    limit = min(limit, 100)
    offset = (page - 1) * limit
    query = db.query(QuizDB).filter(QuizDB.user_id == user.id)
    if q:
        like_pattern = f"%{q}%"
        query = query.filter(
            or_(
                QuizDB.title.ilike(like_pattern),
                QuizDB.description.ilike(like_pattern),
                QuizDB.tags.any(TagDB.name.ilike(like_pattern)),
            )
        )
    total = query.count()
    items = query.options(selectinload(QuizDB.category), selectinload(QuizDB.tags)).order_by(QuizDB.created_at.desc()).offset(offset).limit(limit).all()
    return SearchResult(
        items=[quiz_to_response(q) for q in items],
        page=page, limit=limit, total=total,
    )


def get_quiz(quiz_id: int, db: Session) -> Quiz:
    q = db.query(QuizDB).options(selectinload(QuizDB.category), selectinload(QuizDB.tags)).filter(QuizDB.id == quiz_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quiz não encontrado")
    q.views = (q.views or 0) + 1
    db.commit()
    return quiz_to_response(q)


def create_quiz(data: QuizCreate, user: UserDB, db: Session) -> Quiz:
    if not data.title.strip():
        raise HTTPException(status_code=400, detail="Título é obrigatório")
    if not data.questions:
        raise HTTPException(status_code=400, detail="Adicione ao menos uma pergunta")

    for i, question in enumerate(data.questions):
        if not question.text.strip():
            raise HTTPException(status_code=400, detail=f"Pergunta {i + 1} está vazia")
        if question.type in (QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE, QuestionType.RATING):
            if not question.options or len(question.options) < 2:
                raise HTTPException(
                    status_code=400,
                    detail=f"Pergunta {i + 1} precisa ter ao menos 2 opções",
                )

    q = QuizDB(
        user_id=user.id,
        title=data.title.strip(),
        description=data.description.strip(),
        questions=[qu.model_dump() for qu in data.questions],
        category_id=data.category_id,
    )
    if data.tag_ids:
        tags = db.query(TagDB).filter(TagDB.id.in_(data.tag_ids)).all()
        q.tags = tags
    db.add(q)
    db.commit()
    db.refresh(q)
    logger.info("Quiz criado id=%s usuario=%s titulo=\"%s\"", q.id, user.id, q.title)
    return quiz_to_response(q)


def update_quiz(quiz_id: int, data: QuizUpdate, user: UserDB, db: Session) -> Quiz:
    q = db.query(QuizDB).filter(QuizDB.id == quiz_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quiz não encontrado")
    if q.user_id is None:
        raise HTTPException(status_code=403, detail="Quiz padrão não pode ser editado")
    if q.user_id != user.id:
        raise HTTPException(status_code=403, detail="Você não tem permissão para editar este quiz")

    if data.title is not None:
        if not data.title.strip():
            raise HTTPException(status_code=400, detail="Título não pode ficar vazio")
        q.title = data.title.strip()
    if data.description is not None:
        q.description = data.description.strip()
    if data.questions is not None:
        if not data.questions:
            raise HTTPException(status_code=400, detail="Adicione ao menos uma pergunta")
        for i, qu in enumerate(data.questions):
            if not qu.text.strip():
                raise HTTPException(status_code=400, detail=f"Pergunta {i + 1} está vazia")
        q.questions = [qu.model_dump() for qu in data.questions]
    if data.category_id is not None:
        cat = db.query(CategoryDB).filter(CategoryDB.id == data.category_id).first()
        if not cat:
            raise HTTPException(status_code=400, detail="Categoria não encontrada")
        q.category_id = data.category_id
    if data.tag_ids is not None:
        tags = db.query(TagDB).filter(TagDB.id.in_(data.tag_ids)).all()
        q.tags = tags

    db.commit()
    db.refresh(q)
    logger.info("Quiz atualizado id=%s usuario=%s titulo=\"%s\"", q.id, user.id, q.title)
    return quiz_to_response(q)


def delete_quiz(quiz_id: int, user: UserDB, db: Session):
    q = db.query(QuizDB).filter(QuizDB.id == quiz_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quiz não encontrado")
    if q.user_id is None:
        raise HTTPException(status_code=403, detail="Quiz padrão não pode ser removido")
    if q.user_id != user.id:
        raise HTTPException(status_code=403, detail="Você não tem permissão para remover este quiz")

    db.delete(q)
    db.commit()
    logger.info("Quiz removido id=%s usuario=%s", q.id, user.id)


def list_my_quizzes(user: UserDB, db: Session) -> list[Quiz]:
    quizzes = (
        db.query(QuizDB)
        .options(selectinload(QuizDB.category), selectinload(QuizDB.tags))
        .filter(QuizDB.user_id == user.id)
        .order_by(QuizDB.created_at.desc())
        .all()
    )
    return [quiz_to_response(q) for q in quizzes]


def _get_answer_text(question, answer_value):
    qtype = question.get("type", "text")
    if qtype in ("text", "rating"):
        return str(answer_value) if not isinstance(answer_value, list) else ", ".join(str(v) for v in answer_value)
    options = {str(o["id"]): o["text"] for o in question.get("options", [])}
    if isinstance(answer_value, list):
        return ", ".join(options.get(str(v), str(v)) for v in answer_value)
    return options.get(str(answer_value), str(answer_value))


def _is_correct(question, answer_value):
    qtype = question.get("type", "text")
    if qtype in ("text", "rating"):
        return True
    options = question.get("options", [])
    correct_ids = {str(o["id"]) for o in options if o.get("is_correct")}
    if not correct_ids:
        return True
    if isinstance(answer_value, list):
        user_ids = set(str(v) for v in answer_value)
        return user_ids == correct_ids
    return str(answer_value) in correct_ids


def submit_quiz(quiz_id: int, submission: SubmissionInput, user: UserDB, db: Session) -> SubmissionResponse:
    quiz = db.query(QuizDB).filter(QuizDB.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz não encontrado")

    quiz_questions = {q["id"]: q for q in quiz.questions}
    answers_list = []
    correct_count = 0

    for answer_input in submission.answers:
        question = quiz_questions.get(answer_input.question_id)
        if not question:
            raise HTTPException(
                status_code=400,
                detail=f"Pergunta id {answer_input.question_id} não encontrada no quiz",
            )
        correct = _is_correct(question, answer_input.value)
        if correct:
            correct_count += 1
        answers_list.append(
            AnswerResponse(
                question_id=question["id"],
                question_text=question["text"],
                answer=answer_input.value,
                answer_text=_get_answer_text(question, answer_input.value),
                correct=correct,
            )
        )

    max_score = len(quiz.questions)
    score = correct_count
    percentage = round((score / max_score) * 100) if max_score > 0 else 0

    logger.debug(
        "submit_quiz quiz=%s user=%s: correct=%s/%s score=%s pct=%s  answers=%s",
        quiz_id, user.id, correct_count, max_score, score, percentage,
        [{"q": a.question_id, "correct": a.correct, "answer_text": a.answer_text} for a in answers_list],
    )

    sub = SubmissionDB(
        user_id=user.id,
        quiz_id=quiz_id,
        quiz_title=quiz.title,
        answers=[a.model_dump() for a in answers_list],
        score=score,
        max_score=max_score,
        percentage=percentage,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    return SubmissionResponse(
        id=sub.id,
        user_id=sub.user_id,
        quiz_id=sub.quiz_id,
        quiz_title=sub.quiz_title,
        answers=[AnswerResponse(**a) for a in sub.answers],
        score=sub.score,
        max_score=sub.max_score,
        percentage=sub.percentage,
        created_at=sub.created_at,
    )
