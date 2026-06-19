from __future__ import annotations

from pydantic import BaseModel, EmailStr, ConfigDict
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
    is_correct: bool = False


class Question(BaseModel):
    id: int
    text: str
    type: QuestionType
    options: Optional[List[Option]] = None
    required: bool = True


class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TagResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Quiz(BaseModel):
    id: int
    title: str
    description: str
    questions: List[Question]
    category: Optional[CategoryResponse] = None
    tags: List[TagResponse] = []
    views: int = 0

    model_config = ConfigDict(from_attributes=True)


class QuizCreate(BaseModel):
    title: str
    description: str = ""
    questions: List[Question]
    category_id: Optional[int] = None
    tag_ids: List[int] = []


class QuizUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    questions: Optional[List[Question]] = None
    category_id: Optional[int] = None
    tag_ids: Optional[List[int]] = None


class AnswerInput(BaseModel):
    question_id: int
    value: Union[str, List[str], int]


class SubmissionInput(BaseModel):
    answers: List[AnswerInput]


class AnswerResponse(BaseModel):
    question_id: int
    question_text: str
    answer: Union[str, List[str], int]
    answer_text: str = ""
    correct: bool = True


class SubmissionResponse(BaseModel):
    id: int
    user_id: int
    quiz_id: int
    quiz_title: str
    answers: List[AnswerResponse]
    score: int = 0
    max_score: int = 0
    percentage: int = 0
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

    model_config = ConfigDict(from_attributes=True)


class SetRoleInput(BaseModel):
    role: str


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
    total_admins: int
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
    best_percentage: int = 0
    average_percentage: float = 0
    ranking_position: int = 0
    total_views: int = 0
    most_viewed_quiz: Optional[dict] = None
    recent_quizzes: List[RecentQuizItem] = []
    recent_submissions: List[RecentSubmissionItem] = []


class LeaderboardEntry(BaseModel):
    user_id: int
    name: str
    total_score: int
    submissions: int
    average_percentage: float


class QuizLeaderboardEntry(BaseModel):
    user_id: int
    name: str
    score: int
    max_score: int
    percentage: int


class Badge(BaseModel):
    name: str
    icon: str
    description: str


class QuizSummary(BaseModel):
    id: int
    title: str
    views: int
    created_at: datetime


class PublicProfileResponse(BaseModel):
    id: int
    name: str
    role: str
    quizzes_created: int
    submissions: int
    average_score: float
    best_score: int
    total_views: int = 0
    ranking_position: int = 0
    badges: List[Badge]
    quizzes: List[QuizSummary] = []


class PeriodStats(BaseModel):
    submissions: int
    quizzes_created: int


class StatsResponse(BaseModel):
    last_7_days: PeriodStats
    last_30_days: PeriodStats


class ForgotPasswordInput(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str
    reset_url: Optional[str] = None


class ResetPasswordInput(BaseModel):
    token: str
    new_password: str


class SearchResult(BaseModel):
    items: List[Quiz]
    page: int
    limit: int
    total: int


class ExploreResult(BaseModel):
    items: List[Quiz]
    page: int
    limit: int
    total: int


class SubmissionListResponse(BaseModel):
    items: List[SubmissionResponse]
    page: int
    limit: int
    total: int
