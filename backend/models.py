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
    quiz_id: int
    quiz_title: str
    answers: List[AnswerResponse]


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
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
