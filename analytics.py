"""
Python data analytics module for SmartQuiz Analytics AI.
Uses Pandas and NumPy for performance calculations and recommendations.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer
import pandas as pd
import numpy as np
from .models import (
    User, Quiz, Question, Option, QuizAttempt, StudentResponse,
    Subject, Topic, AttemptStatus
)

def get_student_attempts_df(db: Session, student_id: int) -> pd.DataFrame:
    attempts = (
        db.query(
            QuizAttempt.id,
            QuizAttempt.quiz_id,
            QuizAttempt.score,
            QuizAttempt.percentage,
            QuizAttempt.time_taken_seconds,
            QuizAttempt.submitted_at,
            QuizAttempt.status,
            Quiz.title.label("quiz_title"),
            Subject.name.label("subject"),
            Quiz.difficulty,
            Quiz.total_marks
        )
        .join(Quiz, QuizAttempt.quiz_id == Quiz.id)
        .join(Subject, Quiz.subject_id == Subject.id)
        .filter(
            QuizAttempt.student_id == student_id,
            QuizAttempt.status == AttemptStatus.SUBMITTED
        )
        .all()
    )
    if not attempts:
        return pd.DataFrame()
    return pd.DataFrame([dict(a._mapping) for a in attempts])

def calculate_score_stats(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty:
        return {
            "total_attempts": 0,
            "average_score": 0.0,
            "highest_score": 0.0,
            "lowest_score": 0.0,
            "overall_accuracy": 0.0
        }
    return {
        "total_attempts": int(len(df)),
        "average_score": round(float(df["percentage"].mean()), 2),
        "highest_score": round(float(df["percentage"].max()), 2),
        "lowest_score": round(float(df["percentage"].min()), 2),
        "overall_accuracy": round(float(df["percentage"].mean()), 2)
    }

def subject_wise_performance(db: Session, student_id: int) -> List[Dict]:
    df = get_student_attempts_df(db, student_id)
    if df.empty:
        return []
    grouped = df.groupby("subject").agg(
        attempts=("id", "count"),
        average_score=("percentage", "mean"),
        accuracy=("percentage", "mean")
    ).reset_index()
    return [
        {
            "subject": row["subject"],
            "attempts": int(row["attempts"]),
            "average_score": round(float(row["average_score"]), 2),
            "accuracy": round(float(row["accuracy"]), 2)
        }
        for _, row in grouped.iterrows()
    ]

def topic_wise_performance(db: Session, student_id: int) -> List[Dict]:
    rows = (
        db.query(
            Topic.name.label("topic"),
            Subject.name.label("subject"),
            StudentResponse.is_correct,
            Question.id
        )
        .join(StudentResponse, StudentResponse.question_id == Question.id)
        .join(QuizAttempt, StudentResponse.attempt_id == QuizAttempt.id)
        .outerjoin(Topic, Question.topic_id == Topic.id)
        .outerjoin(Subject, Topic.subject_id == Subject.id)
        .filter(
            QuizAttempt.student_id == student_id,
            QuizAttempt.status == AttemptStatus.SUBMITTED
        )
        .all()
    )
    if not rows:
        return []
    df = pd.DataFrame([dict(r._mapping) for r in rows])
    df["topic"] = df["topic"].fillna("General")
    df["subject"] = df["subject"].fillna("General")
    grouped = df.groupby(["topic", "subject"]).agg(
        correct=("is_correct", "sum"),
        total=("is_correct", "count")
    ).reset_index()
    grouped["accuracy"] = (grouped["correct"] / grouped["total"] * 100).round(2)
    return [
        {
            "topic": row["topic"],
            "subject": row["subject"],
            "correct": int(row["correct"]),
            "total": int(row["total"]),
            "accuracy": float(row["accuracy"])
        }
        for _, row in grouped.iterrows()
    ]

def progress_over_time(db: Session, student_id: int) -> List[Dict]:
    df = get_student_attempts_df(db, student_id)
    if df.empty:
        return []
    df = df.sort_values("submitted_at")
    return [
        {
            "date": row["submitted_at"].isoformat() if row["submitted_at"] else None,
            "quiz": row["quiz_title"],
            "percentage": round(float(row["percentage"]), 2),
            "subject": row["subject"]
        }
        for _, row in df.iterrows()
    ]

def generate_recommendations(db: Session, student_id: int) -> List[str]:
    recommendations = []
    subject_perf = subject_wise_performance(db, student_id)
    topic_perf = topic_wise_performance(db, student_id)
    df = get_student_attempts_df(db, student_id)
    
    if df.empty:
        recommendations.append("Take your first quiz to unlock personalized recommendations.")
        return recommendations
    
    # Strong subjects
    strong = [s for s in subject_perf if s["average_score"] >= 80]
    for s in strong[:2]:
        recommendations.append(f"Your {s['subject']} performance is strong (avg {s['average_score']}%). Keep it up!")
    
    # Weak subjects
    weak = [s for s in subject_perf if s["average_score"] < 60]
    for s in weak[:2]:
        recommendations.append(f"Practice more {s['subject']} quizzes to improve your accuracy (currently {s['average_score']}%).")
    
    # Weak topics
    weak_topics = sorted([t for t in topic_perf if t["accuracy"] < 50 and t["total"] >= 2], key=lambda x: x["accuracy"])
    for t in weak_topics[:3]:
        recommendations.append(f"Practice {t['topic']} in {t['subject']} — accuracy is only {t['accuracy']}%.")
    
    # Improvement
    if len(df) >= 2:
        recent = df.sort_values("submitted_at").tail(2)
        prev = float(recent.iloc[0]["percentage"])
        curr = float(recent.iloc[1]["percentage"])
        diff = round(curr - prev, 1)
        if diff > 5:
            recommendations.append(f"Your accuracy improved by {diff} percentage points compared with your previous quiz.")
        elif diff < -5:
            recommendations.append(f"Your recent score dropped by {abs(diff)} points. Review the topics you missed.")
    
    # Difficulty suggestion
    avg = float(df["percentage"].mean())
    if avg >= 85:
        recommendations.append("Try an intermediate or advanced level quiz to challenge yourself.")
    elif avg < 50:
        recommendations.append("Start with beginner-level quizzes to build a solid foundation.")
    
    if not recommendations:
        recommendations.append("Keep practicing regularly to improve your performance.")
    
    return recommendations[:6]

def score_distribution(db: Session, student_id: Optional[int] = None, quiz_id: Optional[int] = None) -> Dict:
    q = db.query(QuizAttempt.percentage).filter(QuizAttempt.status == AttemptStatus.SUBMITTED)
    if student_id:
        q = q.filter(QuizAttempt.student_id == student_id)
    if quiz_id:
        q = q.filter(QuizAttempt.quiz_id == quiz_id)
    scores = [r[0] for r in q.all()]
    if not scores:
        return {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
    bins = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
    for s in scores:
        if s <= 20: bins["0-20"] += 1
        elif s <= 40: bins["21-40"] += 1
        elif s <= 60: bins["41-60"] += 1
        elif s <= 80: bins["61-80"] += 1
        else: bins["81-100"] += 1
    return bins

def class_average_for_quiz(db: Session, quiz_id: int) -> Dict:
    attempts = db.query(QuizAttempt).filter(
        QuizAttempt.quiz_id == quiz_id,
        QuizAttempt.status == AttemptStatus.SUBMITTED
    ).all()
    if not attempts:
        return {"average": 0, "count": 0, "highest": 0, "lowest": 0}
    scores = [a.percentage for a in attempts]
    return {
        "average": round(float(np.mean(scores)), 2),
        "count": len(scores),
        "highest": round(float(np.max(scores)), 2),
        "lowest": round(float(np.min(scores)), 2)
    }

def identify_weak_topics_class(db: Session, quiz_id: int) -> List[Dict]:
    rows = (
        db.query(
            Topic.name.label("topic"),
            func.sum(StudentResponse.is_correct.cast(Integer) if False else StudentResponse.is_correct).label("correct"),
            func.count(StudentResponse.id).label("total")
        )
        .select_from(StudentResponse)
        .join(QuizAttempt, StudentResponse.attempt_id == QuizAttempt.id)
        .join(Question, StudentResponse.question_id == Question.id)
        .outerjoin(Topic, Question.topic_id == Topic.id)
        .filter(QuizAttempt.quiz_id == quiz_id, QuizAttempt.status == AttemptStatus.SUBMITTED)
        .group_by(Topic.name)
        .all()
    )
    # Simpler approach
    responses = (
        db.query(StudentResponse, Question, Topic)
        .join(QuizAttempt)
        .join(Question)
        .outerjoin(Topic, Question.topic_id == Topic.id)
        .filter(QuizAttempt.quiz_id == quiz_id, QuizAttempt.status == AttemptStatus.SUBMITTED)
        .all()
    )
    if not responses:
        return []
    data = []
    for resp, q, topic in responses:
        data.append({
            "topic": topic.name if topic else "General",
            "is_correct": resp.is_correct
        })
    df = pd.DataFrame(data)
    grouped = df.groupby("topic").agg(correct=("is_correct", "sum"), total=("is_correct", "count")).reset_index()
    grouped["accuracy"] = (grouped["correct"] / grouped["total"] * 100).round(2)
    weak = grouped[grouped["accuracy"] < 60].sort_values("accuracy")
    return [
        {"topic": row["topic"], "accuracy": float(row["accuracy"]), "total": int(row["total"])}
        for _, row in weak.iterrows()
    ]

def get_performance_classification(percentage: float) -> str:
    if percentage >= 90:
        return "Excellent"
    elif percentage >= 75:
        return "Good"
    elif percentage >= 60:
        return "Average"
    elif percentage >= 40:
        return "Needs Improvement"
    else:
        return "Poor"
