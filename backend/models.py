from __future__ import annotations

from pydantic import BaseModel, EmailStr
from typing import List, Optional, Union
from enum import Enum
from datetime import datetime


class QuestionType(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    SINGLE_CHOICE = "single_choice"
    TEXT = "text"
    RATING = "rating"


class Option(BaseModel):
    id: int
    text: str


class Question(BaseModel):
    id: int
    text: str
    type: QuestionType
    options: Optional[List[Option]] = None
    required: bool = True


class Quiz(BaseModel):
    id: int
    title: str
    description: str
    questions: List[Question]

    class Config:
        from_attributes = True


class QuizCreate(BaseModel):
    title: str
    description: str = ""
    questions: List[Question]


class QuizUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    questions: Optional[List[Question]] = None


class AnswerInput(BaseModel):
    question_id: int
    value: Union[str, List[str], int]


class SubmissionInput(BaseModel):
    answers: List[AnswerInput]


class AnswerResponse(BaseModel):
    question_id: int
    question_text: str
    answer: Union[str, List[str], int]


class SubmissionResponse(BaseModel):
    id: int
    user_id: int
    quiz_id: int
    quiz_title: str
    answers: List[AnswerResponse]
    created_at: datetime


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str = "user"
    created_at: datetime

    class Config:
        from_attributes = True


class AdminUserItem(BaseModel):
    id: int
    name: str
    email: str
    role: str
    created_at: datetime
    quizzes_count: int = 0
    submissions_count: int = 0


class AdminDashboardResponse(BaseModel):
    total_users: int
    total_quizzes: int
    total_submissions: int
    users: List[AdminUserItem]


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenInput(BaseModel):
    refresh_token: str


class SessionResponse(BaseModel):
    id: int
    created_at: datetime
    last_used_at: Optional[datetime] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None


class RecentQuizItem(BaseModel):
    id: int
    title: str
    created_at: datetime


class RecentSubmissionItem(BaseModel):
    id: int
    quiz_id: int
    quiz_title: str
    created_at: datetime


class DashboardResponse(BaseModel):
    total_quizzes_created: int
    total_quizzes_responded: int
    total_submissions: int
    total_answers_submitted: int
    recent_quizzes: List[RecentQuizItem] = []
    recent_submissions: List[RecentSubmissionItem] = []


class PeriodStats(BaseModel):
    submissions: int
    quizzes_created: int


class StatsResponse(BaseModel):
    last_7_days: PeriodStats
    last_30_days: PeriodStats
