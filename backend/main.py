import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from models import Quiz, SubmissionInput, SubmissionResponse, AnswerResponse
from database import quiz_database, submissions, get_submission_counter

app = FastAPI(title="Quiz App API", description="Backend para formulários de pesquisa e quiz")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/quizzes", response_model=list[Quiz])
def list_quizzes():
    return list(quiz_database.values())


@app.get("/quizzes/{quiz_id}", response_model=Quiz)
def get_quiz(quiz_id: int):
    quiz = quiz_database.get(quiz_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz não encontrado")
    return quiz


@app.post("/quizzes/{quiz_id}/submit", response_model=SubmissionResponse)
def submit_quiz(quiz_id: int, submission: SubmissionInput):
    quiz = quiz_database.get(quiz_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz não encontrado")

    quiz_questions = {q.id: q for q in quiz.questions}
    answers_list = []

    for answer_input in submission.answers:
        question = quiz_questions.get(answer_input.question_id)
        if not question:
            raise HTTPException(
                status_code=400,
                detail=f"Pergunta id {answer_input.question_id} não encontrada no quiz",
            )
        answers_list.append(
            AnswerResponse(
                question_id=question.id,
                question_text=question.text,
                answer=answer_input.value,
            )
        )

    sub_id = get_submission_counter()
    response = SubmissionResponse(
        id=sub_id,
        quiz_id=quiz_id,
        quiz_title=quiz.title,
        answers=answers_list,
    )

    submissions.append(response.model_dump())
    return response


@app.get("/submissions", response_model=list[SubmissionResponse])
def list_submissions():
    return submissions


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
