from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base

class UserRole(str, enum.Enum):
    STUDENT = "student"
    TEACHER = "teacher"

class Difficulty(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class AttemptStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    EXPIRED = "expired"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(150), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.STUDENT)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    quizzes_created = relationship("Quiz", back_populates="creator")
    attempts = relationship("QuizAttempt", back_populates="student")

class Subject(Base):
    __tablename__ = "subjects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    
    topics = relationship("Topic", back_populates="subject")
    quizzes = relationship("Quiz", back_populates="subject")

class Topic(Base):
    __tablename__ = "topics"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    
    subject = relationship("Subject", back_populates="topics")
    questions = relationship("Question", back_populates="topic")

class Quiz(Base):
    __tablename__ = "quizzes"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    difficulty = Column(SQLEnum(Difficulty), default=Difficulty.BEGINNER)
    duration_minutes = Column(Integer, default=30)
    total_marks = Column(Integer, default=0)
    is_published = Column(Boolean, default=False)
    show_answers_after = Column(Boolean, default=True)
    attempt_limit = Column(Integer, default=1)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    available_from = Column(DateTime, nullable=True)
    available_to = Column(DateTime, nullable=True)
    
    subject = relationship("Subject", back_populates="quizzes")
    creator = relationship("User", back_populates="quizzes_created")
    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan")
    attempts = relationship("QuizAttempt", back_populates="quiz")

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    text = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)
    marks = Column(Integer, default=1)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    order = Column(Integer, default=0)
    
    quiz = relationship("Quiz", back_populates="questions")
    topic = relationship("Topic", back_populates="questions")
    options = relationship("Option", back_populates="question", cascade="all, delete-orphan")
    responses = relationship("StudentResponse", back_populates="question")

class Option(Base):
    __tablename__ = "options"
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False)
    order = Column(Integer, default=0)
    
    question = relationship("Question", back_populates="options")

class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)
    score = Column(Float, default=0.0)
    percentage = Column(Float, default=0.0)
    time_taken_seconds = Column(Integer, default=0)
    status = Column(SQLEnum(AttemptStatus), default=AttemptStatus.IN_PROGRESS)
    
    quiz = relationship("Quiz", back_populates="attempts")
    student = relationship("User", back_populates="attempts")
    responses = relationship("StudentResponse", back_populates="attempt", cascade="all, delete-orphan")

class StudentResponse(Base):
    __tablename__ = "student_responses"
    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("quiz_attempts.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    selected_option_id = Column(Integer, ForeignKey("options.id"), nullable=True)
    is_correct = Column(Boolean, default=False)
    time_spent_seconds = Column(Integer, default=0)
    marked_for_review = Column(Boolean, default=False)
    
    attempt = relationship("QuizAttempt", back_populates="responses")
    question = relationship("Question", back_populates="responses")
