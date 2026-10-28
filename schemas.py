from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"

class Difficulty(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

# Auth
class UserCreate(BaseModel):
    email: str
    password: str = Field(..., min_length=6)
    name: str
    role: UserRole = UserRole.STUDENT

class UserLogin(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: UserRole
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

# Subjects / Topics
class SubjectOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class TopicOut(BaseModel):
    id: int
    name: str
    subject_id: int
    model_config = ConfigDict(from_attributes=True)

# Options
class OptionCreate(BaseModel):
    text: str
    is_correct: bool = False
    order: int = 0

class OptionOut(BaseModel):
    id: int
    text: str
    order: int
    # is_correct intentionally omitted for students before submission
    model_config = ConfigDict(from_attributes=True)

class OptionWithAnswer(OptionOut):
    is_correct: bool

# Questions
class QuestionCreate(BaseModel):
    text: str
    explanation: Optional[str] = None
    marks: int = 1
    topic_id: Optional[int] = None
    order: int = 0
    options: List[OptionCreate]

class QuestionOut(BaseModel):
    id: int
    text: str
    marks: int
    order: int
    topic_id: Optional[int]
    options: List[OptionOut]
    model_config = ConfigDict(from_attributes=True)

class QuestionWithAnswer(BaseModel):
    id: int
    text: str
    explanation: Optional[str]
    marks: int
    order: int
    topic_id: Optional[int]
    options: List[OptionWithAnswer]
    model_config = ConfigDict(from_attributes=True)

# Quiz
class QuizCreate(BaseModel):
    title: str
    description: Optional[str] = None
    subject_id: int
    difficulty: Difficulty = Difficulty.BEGINNER
    duration_minutes: int = 30
    show_answers_after: bool = True
    attempt_limit: int = 1
    questions: List[QuestionCreate] = []

class QuizUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    duration_minutes: Optional[int] = None
    is_published: Optional[bool] = None
    show_answers_after: Optional[bool] = None
    attempt_limit: Optional[int] = None

class QuizOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    subject_id: int
    subject: Optional[SubjectOut] = None
    difficulty: Difficulty
    duration_minutes: int
    total_marks: int
    is_published: bool
    show_answers_after: bool
    attempt_limit: int
    created_by_id: int
    created_at: datetime
    question_count: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

class QuizDetail(QuizOut):
    questions: List[QuestionOut] = []

# Attempts
class ResponseSubmit(BaseModel):
    question_id: int
    selected_option_id: Optional[int] = None
    time_spent_seconds: int = 0
    marked_for_review: bool = False

class AttemptStart(BaseModel):
    quiz_id: int

class AttemptSubmit(BaseModel):
    responses: List[ResponseSubmit]

class AttemptOut(BaseModel):
    id: int
    quiz_id: int
    student_id: int
    started_at: datetime
    submitted_at: Optional[datetime]
    score: float
    percentage: float
    time_taken_seconds: int
    status: str
    model_config = ConfigDict(from_attributes=True)

class ResultDetail(BaseModel):
    attempt: AttemptOut
    total_questions: int
    correct: int
    incorrect: int
    unanswered: int
    marks_obtained: float
    total_marks: float
    percentage: float
    accuracy: float
    time_taken_seconds: int
    classification: str
    questions: Optional[List[dict]] = None  # with answers if allowed

# Analytics
class StudentDashboardStats(BaseModel):
    total_attempts: int
    average_score: float
    highest_score: float
    overall_accuracy: float
    recent_attempts: List[dict]
    available_quizzes: List[QuizOut]
    recommendations: List[str]
    progress_trend: List[dict]

class SubjectPerformance(BaseModel):
    subject: str
    attempts: int
    average_score: float
    accuracy: float

class TopicPerformance(BaseModel):
    topic: str
    subject: str
    correct: int
    total: int
    accuracy: float

class AnalyticsOverview(BaseModel):
    score_stats: dict
    subject_wise: List[SubjectPerformance]
    topic_wise: List[TopicPerformance]
    progress_over_time: List[dict]
    recommendations: List[str]
    score_distribution: dict
