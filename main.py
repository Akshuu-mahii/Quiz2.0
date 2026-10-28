from fastapi import FastAPI, Depends, HTTPException, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, timedelta
import csv
import io
import os

from .database import engine, Base, get_db, SessionLocal
from .models import (
    User, Subject, Topic, Quiz, Question, Option, QuizAttempt, StudentResponse,
    UserRole, AttemptStatus, Difficulty
)
from .schemas import (
    UserCreate, UserLogin, UserOut, Token, QuizCreate, QuizUpdate, QuizOut, QuizDetail,
    QuestionCreate, QuestionOut, OptionOut, AttemptStart, AttemptSubmit, AttemptOut, ResultDetail,
    StudentDashboardStats, AnalyticsOverview
)
from .auth import (
    get_password_hash, authenticate_user, create_access_token,
    get_current_user, get_current_student, get_current_teacher
)
from . import analytics as analytics_mod

app = FastAPI(title="SmartQuiz Analytics AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables
Base.metadata.create_all(bind=engine)

# ---------- AUTH ----------
@app.post("/api/auth/register", response_model=Token)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        name=user_in.name,
        role=user_in.role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token, user=UserOut.model_validate(user))

@app.post("/api/auth/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token, user=UserOut.model_validate(user))

@app.get("/api/auth/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user

# ---------- PUBLIC / STATS ----------
@app.get("/api/stats")
def platform_stats(db: Session = Depends(get_db)):
    return {
        "total_quizzes": db.query(Quiz).filter(Quiz.is_published == True).count(),
        "total_students": db.query(User).filter(User.role == UserRole.STUDENT).count(),
        "total_attempts": db.query(QuizAttempt).filter(QuizAttempt.status == AttemptStatus.SUBMITTED).count(),
        "total_teachers": db.query(User).filter(User.role == UserRole.TEACHER).count()
    }

# ---------- SUBJECTS ----------
@app.get("/api/subjects")
def list_subjects(db: Session = Depends(get_db)):
    return db.query(Subject).all()

# ---------- STUDENT: AVAILABLE QUIZZES ----------
@app.get("/api/quizzes", response_model=List[QuizOut])
def list_published_quizzes(
    subject_id: Optional[int] = None,
    difficulty: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    q = db.query(Quiz).options(joinedload(Quiz.subject)).filter(Quiz.is_published == True)
    if subject_id:
        q = q.filter(Quiz.subject_id == subject_id)
    if difficulty:
        q = q.filter(Quiz.difficulty == difficulty)
    if search:
        q = q.filter(Quiz.title.ilike(f"%{search}%"))
    quizzes = q.order_by(Quiz.created_at.desc()).all()
    result = []
    for quiz in quizzes:
        out = QuizOut.model_validate(quiz)
        out.question_count = len(quiz.questions)
        out.subject = quiz.subject
        result.append(out)
    return result

@app.get("/api/quizzes/{quiz_id}", response_model=QuizDetail)
def get_quiz_for_attempt(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_student)
):
    quiz = db.query(Quiz).options(
        joinedload(Quiz.questions).joinedload(Question.options),
        joinedload(Quiz.subject)
    ).filter(Quiz.id == quiz_id, Quiz.is_published == True).first()
    if not quiz:
        raise HTTPException(404, "Quiz not found")
    # Check attempt limit
    prev = db.query(QuizAttempt).filter(
        QuizAttempt.quiz_id == quiz_id,
        QuizAttempt.student_id == current_user.id,
        QuizAttempt.status == AttemptStatus.SUBMITTED
    ).count()
    if prev >= quiz.attempt_limit:
        raise HTTPException(400, "Attempt limit reached for this quiz")
    # Return without correct answers
    detail = QuizDetail.model_validate(quiz)
    detail.subject = quiz.subject
    detail.questions = []
    for q in sorted(quiz.questions, key=lambda x: x.order):
        opts = [OptionOut.model_validate(o) for o in sorted(q.options, key=lambda x: x.order)]
        detail.questions.append(QuestionOut(
            id=q.id, text=q.text, marks=q.marks, order=q.order,
            topic_id=q.topic_id, options=opts
        ))
    return detail

# ---------- ATTEMPTS ----------
@app.post("/api/attempts/start", response_model=AttemptOut)
def start_attempt(
    body: AttemptStart,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_student)
):
    quiz = db.query(Quiz).filter(Quiz.id == body.quiz_id, Quiz.is_published == True).first()
    if not quiz:
        raise HTTPException(404, "Quiz not found")
    # Cancel any in-progress
    existing = db.query(QuizAttempt).filter(
        QuizAttempt.quiz_id == body.quiz_id,
        QuizAttempt.student_id == current_user.id,
        QuizAttempt.status == AttemptStatus.IN_PROGRESS
    ).first()
    if existing:
        return existing
    attempt = QuizAttempt(
        quiz_id=body.quiz_id,
        student_id=current_user.id,
        status=AttemptStatus.IN_PROGRESS
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt

@app.post("/api/attempts/{attempt_id}/submit", response_model=ResultDetail)
def submit_attempt(
    attempt_id: int,
    body: AttemptSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_student)
):
    attempt = db.query(QuizAttempt).options(
        joinedload(QuizAttempt.quiz).joinedload(Quiz.questions).joinedload(Question.options)
    ).filter(QuizAttempt.id == attempt_id, QuizAttempt.student_id == current_user.id).first()
    if not attempt:
        raise HTTPException(404, "Attempt not found")
    if attempt.status != AttemptStatus.IN_PROGRESS:
        raise HTTPException(400, "Attempt already submitted")
    
    quiz = attempt.quiz
    correct_map = {}
    for q in quiz.questions:
        for o in q.options:
            if o.is_correct:
                correct_map[q.id] = o.id
                break
    
    score = 0.0
    correct_count = 0
    incorrect_count = 0
    unanswered = 0
    total_marks = quiz.total_marks or sum(q.marks for q in quiz.questions)
    
    for resp in body.responses:
        is_corr = False
        if resp.selected_option_id and resp.question_id in correct_map:
            is_corr = resp.selected_option_id == correct_map[resp.question_id]
            if is_corr:
                # find marks
                q = next((x for x in quiz.questions if x.id == resp.question_id), None)
                if q:
                    score += q.marks
                    correct_count += 1
            else:
                incorrect_count += 1
        else:
            unanswered += 1
        
        sr = StudentResponse(
            attempt_id=attempt.id,
            question_id=resp.question_id,
            selected_option_id=resp.selected_option_id,
            is_correct=is_corr,
            time_spent_seconds=resp.time_spent_seconds,
            marked_for_review=resp.marked_for_review
        )
        db.add(sr)
    
    percentage = round((score / total_marks * 100) if total_marks else 0, 2)
    time_taken = int((datetime.utcnow() - attempt.started_at).total_seconds())
    
    attempt.score = score
    attempt.percentage = percentage
    attempt.time_taken_seconds = time_taken
    attempt.submitted_at = datetime.utcnow()
    attempt.status = AttemptStatus.SUBMITTED
    db.commit()
    db.refresh(attempt)
    
    classification = analytics_mod.get_performance_classification(percentage)
    
    questions_detail = None
    if quiz.show_answers_after:
        questions_detail = []
        for q in sorted(quiz.questions, key=lambda x: x.order):
            selected = next((r.selected_option_id for r in body.responses if r.question_id == q.id), None)
            questions_detail.append({
                "id": q.id,
                "text": q.text,
                "explanation": q.explanation,
                "marks": q.marks,
                "options": [{"id": o.id, "text": o.text, "is_correct": o.is_correct} for o in q.options],
                "selected_option_id": selected,
                "is_correct": selected == correct_map.get(q.id) if selected else False
            })
    
    return ResultDetail(
        attempt=AttemptOut.model_validate(attempt),
        total_questions=len(quiz.questions),
        correct=correct_count,
        incorrect=incorrect_count,
        unanswered=unanswered,
        marks_obtained=score,
        total_marks=total_marks,
        percentage=percentage,
        accuracy=percentage,
        time_taken_seconds=time_taken,
        classification=classification,
        questions=questions_detail
    )

@app.get("/api/attempts/{attempt_id}/result", response_model=ResultDetail)
def get_result(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    attempt = db.query(QuizAttempt).options(
        joinedload(QuizAttempt.quiz).joinedload(Quiz.questions).joinedload(Question.options),
        joinedload(QuizAttempt.responses)
    ).filter(QuizAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(404, "Not found")
    if current_user.role == UserRole.STUDENT and attempt.student_id != current_user.id:
        raise HTTPException(403, "Forbidden")
    
    quiz = attempt.quiz
    total_marks = quiz.total_marks or sum(q.marks for q in quiz.questions)
    correct = sum(1 for r in attempt.responses if r.is_correct)
    incorrect = sum(1 for r in attempt.responses if r.selected_option_id and not r.is_correct)
    unanswered = len(quiz.questions) - correct - incorrect
    
    questions_detail = None
    if quiz.show_answers_after or current_user.role == UserRole.TEACHER:
        correct_map = {q.id: next((o.id for o in q.options if o.is_correct), None) for q in quiz.questions}
        questions_detail = []
        for q in sorted(quiz.questions, key=lambda x: x.order):
            resp = next((r for r in attempt.responses if r.question_id == q.id), None)
            questions_detail.append({
                "id": q.id,
                "text": q.text,
                "explanation": q.explanation,
                "marks": q.marks,
                "options": [{"id": o.id, "text": o.text, "is_correct": o.is_correct} for o in q.options],
                "selected_option_id": resp.selected_option_id if resp else None,
                "is_correct": resp.is_correct if resp else False
            })
    
    return ResultDetail(
        attempt=AttemptOut.model_validate(attempt),
        total_questions=len(quiz.questions),
        correct=correct,
        incorrect=incorrect,
        unanswered=unanswered,
        marks_obtained=attempt.score,
        total_marks=total_marks,
        percentage=attempt.percentage,
        accuracy=attempt.percentage,
        time_taken_seconds=attempt.time_taken_seconds,
        classification=analytics_mod.get_performance_classification(attempt.percentage),
        questions=questions_detail
    )

# ---------- STUDENT DASHBOARD & ANALYTICS ----------
@app.get("/api/student/dashboard")
def student_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_student)
):
    df = analytics_mod.get_student_attempts_df(db, current_user.id)
    stats = analytics_mod.calculate_score_stats(df)
    recent = analytics_mod.progress_over_time(db, current_user.id)[-5:][::-1]
    available = db.query(Quiz).options(joinedload(Quiz.subject)).filter(Quiz.is_published == True).limit(6).all()
    available_out = []
    for q in available:
        o = QuizOut.model_validate(q)
        o.subject = q.subject
        o.question_count = len(q.questions)
        available_out.append(o)
    recs = analytics_mod.generate_recommendations(db, current_user.id)
    return {
        "welcome": f"Welcome back, {current_user.name}!",
        "stats": stats,
        "recent_attempts": recent,
        "available_quizzes": available_out,
        "recommendations": recs,
        "progress_trend": analytics_mod.progress_over_time(db, current_user.id)
    }

@app.get("/api/student/analytics", response_model=AnalyticsOverview)
def student_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_student)
):
    df = analytics_mod.get_student_attempts_df(db, current_user.id)
    return AnalyticsOverview(
        score_stats=analytics_mod.calculate_score_stats(df),
        subject_wise=analytics_mod.subject_wise_performance(db, current_user.id),
        topic_wise=analytics_mod.topic_wise_performance(db, current_user.id),
        progress_over_time=analytics_mod.progress_over_time(db, current_user.id),
        recommendations=analytics_mod.generate_recommendations(db, current_user.id),
        score_distribution=analytics_mod.score_distribution(db, student_id=current_user.id)
    )

@app.get("/api/student/history")
def student_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_student)
):
    attempts = (
        db.query(QuizAttempt)
        .options(joinedload(QuizAttempt.quiz).joinedload(Quiz.subject))
        .filter(QuizAttempt.student_id == current_user.id, QuizAttempt.status == AttemptStatus.SUBMITTED)
        .order_by(QuizAttempt.submitted_at.desc())
        .all()
    )
    return [
        {
            "id": a.id,
            "quiz_title": a.quiz.title,
            "subject": a.quiz.subject.name if a.quiz.subject else None,
            "score": a.score,
            "percentage": a.percentage,
            "time_taken_seconds": a.time_taken_seconds,
            "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
            "classification": analytics_mod.get_performance_classification(a.percentage)
        }
        for a in attempts
    ]

# ---------- TEACHER ----------
@app.post("/api/teacher/quizzes", response_model=QuizOut)
def create_quiz(
    body: QuizCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher)
):
    total_marks = sum(q.marks for q in body.questions)
    quiz = Quiz(
        title=body.title,
        description=body.description,
        subject_id=body.subject_id,
        difficulty=body.difficulty,
        duration_minutes=body.duration_minutes,
        total_marks=total_marks,
        show_answers_after=body.show_answers_after,
        attempt_limit=body.attempt_limit,
        created_by_id=current_user.id,
        is_published=False
    )
    db.add(quiz)
    db.flush()
    for i, q_in in enumerate(body.questions):
        q = Question(
            quiz_id=quiz.id,
            text=q_in.text,
            explanation=q_in.explanation,
            marks=q_in.marks,
            topic_id=q_in.topic_id,
            order=q_in.order or i
        )
        db.add(q)
        db.flush()
        for j, o_in in enumerate(q_in.options):
            o = Option(
                question_id=q.id,
                text=o_in.text,
                is_correct=o_in.is_correct,
                order=o_in.order or j
            )
            db.add(o)
    db.commit()
    db.refresh(quiz)
    return QuizOut.model_validate(quiz)

@app.get("/api/teacher/quizzes", response_model=List[QuizOut])
def teacher_quizzes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher)
):
    quizzes = db.query(Quiz).options(joinedload(Quiz.subject)).filter(Quiz.created_by_id == current_user.id).all()
    result = []
    for q in quizzes:
        out = QuizOut.model_validate(q)
        out.subject = q.subject
        out.question_count = len(q.questions)
        result.append(out)
    return result

@app.patch("/api/teacher/quizzes/{quiz_id}", response_model=QuizOut)
def update_quiz(
    quiz_id: int,
    body: QuizUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher)
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.created_by_id == current_user.id).first()
    if not quiz:
        raise HTTPException(404, "Quiz not found")
    for k, v in body.dict(exclude_unset=True).items():
        setattr(quiz, k, v)
    db.commit()
    db.refresh(quiz)
    return QuizOut.model_validate(quiz)

@app.delete("/api/teacher/quizzes/{quiz_id}")
def delete_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher)
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.created_by_id == current_user.id).first()
    if not quiz:
        raise HTTPException(404, "Not found")
    db.delete(quiz)
    db.commit()
    return {"ok": True}

@app.get("/api/teacher/quizzes/{quiz_id}/results")
def quiz_results(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher)
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.created_by_id == current_user.id).first()
    if not quiz:
        raise HTTPException(404, "Not found")
    attempts = (
        db.query(QuizAttempt)
        .options(joinedload(QuizAttempt.student))
        .filter(QuizAttempt.quiz_id == quiz_id, QuizAttempt.status == AttemptStatus.SUBMITTED)
        .order_by(QuizAttempt.percentage.desc())
        .all()
    )
    class_avg = analytics_mod.class_average_for_quiz(db, quiz_id)
    weak = analytics_mod.identify_weak_topics_class(db, quiz_id)
    return {
        "quiz": QuizOut.model_validate(quiz),
        "attempts": [
            {
                "id": a.id,
                "student_name": a.student.name,
                "student_email": a.student.email,
                "score": a.score,
                "percentage": a.percentage,
                "time_taken_seconds": a.time_taken_seconds,
                "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None
            }
            for a in attempts
        ],
        "class_average": class_avg,
        "weak_topics": weak,
        "score_distribution": analytics_mod.score_distribution(db, quiz_id=quiz_id)
    }

@app.get("/api/teacher/export/{quiz_id}")
def export_csv(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher)
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.created_by_id == current_user.id).first()
    if not quiz:
        raise HTTPException(404, "Not found")
    attempts = (
        db.query(QuizAttempt)
        .options(joinedload(QuizAttempt.student))
        .filter(QuizAttempt.quiz_id == quiz_id, QuizAttempt.status == AttemptStatus.SUBMITTED)
        .all()
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student Name", "Email", "Score", "Percentage", "Time (s)", "Submitted At"])
    for a in attempts:
        writer.writerow([
            a.student.name, a.student.email, a.score, a.percentage,
            a.time_taken_seconds, a.submitted_at.isoformat() if a.submitted_at else ""
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=quiz_{quiz_id}_results.csv"}
    )

@app.get("/api/teacher/students")
def list_students(db: Session = Depends(get_db), current_user: User = Depends(get_current_teacher)):
    students = db.query(User).filter(User.role == UserRole.STUDENT).all()
    return [{"id": s.id, "name": s.name, "email": s.email} for s in students]

# ---------- SEED ----------
@app.on_event("startup")
def seed_data():
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            return
        # Users
        teacher = User(
            email="teacher@smartquiz.ai",
            hashed_password=get_password_hash("teacher123"),
            name="Dr. Sarah Chen",
            role=UserRole.TEACHER
        )
        student = User(
            email="student@smartquiz.ai",
            hashed_password=get_password_hash("student123"),
            name="Alex Rivera",
            role=UserRole.STUDENT
        )
        student2 = User(
            email="student2@smartquiz.ai",
            hashed_password=get_password_hash("student123"),
            name="Jordan Lee",
            role=UserRole.STUDENT
        )
        db.add_all([teacher, student, student2])
        db.flush()
        
        # Subjects & Topics
        subjects_data = [
            ("Python Programming", "Core Python concepts and libraries"),
            ("SQL & Databases", "Relational databases and SQL queries"),
            ("Data Structures", "Arrays, lists, trees, graphs and algorithms"),
            ("Web Development", "HTML, CSS, JavaScript and frameworks")
        ]
        subjects = []
        for name, desc in subjects_data:
            s = Subject(name=name, description=desc)
            db.add(s)
            subjects.append(s)
        db.flush()
        
        topics_map = {
            subjects[0].id: ["Variables & Types", "Control Flow", "Functions", "OOP", "Modules"],
            subjects[1].id: ["SELECT Queries", "Joins", "Aggregations", "Indexes", "Normalization"],
            subjects[2].id: ["Arrays & Lists", "Stacks & Queues", "Trees", "Sorting", "Searching"],
            subjects[3].id: ["HTML Basics", "CSS Layout", "JavaScript DOM", "React Basics", "APIs"]
        }
        topic_objs = {}
        for sid, names in topics_map.items():
            for n in names:
                t = Topic(name=n, subject_id=sid)
                db.add(t)
                topic_objs[(sid, n)] = t
        db.flush()
        
        # Sample Quiz 1 - Python Basics
        q1 = Quiz(
            title="Python Fundamentals Quiz",
            description="Test your knowledge of Python basics including variables, control flow and functions.",
            subject_id=subjects[0].id,
            difficulty=Difficulty.BEGINNER,
            duration_minutes=15,
            total_marks=10,
            is_published=True,
            show_answers_after=True,
            attempt_limit=3,
            created_by_id=teacher.id
        )
        db.add(q1)
        db.flush()
        
        questions_data = [
            ("What is the output of print(type(5))?", "int type", 1, "Variables & Types",
             [(" <class 'int'> ", True), (" <class 'str'> ", False), (" <class 'float'> ", False), (" int ", False)]),
            ("Which keyword is used to define a function in Python?", None, 1, "Functions",
             [("func", False), ("def", True), ("function", False), ("define", False)]),
            ("What does the 'len()' function do?", None, 1, "Functions",
             [("Returns the length of an object", True), ("Returns the type", False), ("Sorts a list", False), ("Converts to string", False)]),
            ("Which of the following is a mutable data type?", None, 1, "Variables & Types",
             [("tuple", False), ("list", True), ("str", False), ("int", False)]),
            ("What is the correct way to create a list?", None, 1, "Variables & Types",
             [("list = (1,2,3)", False), ("list = [1,2,3]", True), ("list = {1,2,3}", False), ("list = <1,2,3>", False)]),
            ("How do you start a for loop in Python?", None, 1, "Control Flow",
             [("for x in y:", True), ("for (x in y)", False), ("foreach x in y", False), ("loop x in y", False)]),
            ("What is the result of 10 // 3?", None, 1, "Variables & Types",
             [("3.33", False), ("3", True), ("4", False), ("3.0", False)]),
            ("Which statement is used to handle exceptions?", None, 1, "Control Flow",
             [("try-except", True), ("do-catch", False), ("if-error", False), ("catch-throw", False)]),
            ("What does 'self' represent in a class method?", None, 1, "OOP",
             [("The class itself", False), ("The instance of the class", True), ("A global variable", False), ("The parent class", False)]),
            ("How do you import a module named 'math'?", None, 1, "Modules",
             [("include math", False), ("import math", True), ("using math", False), ("require math", False)]),
        ]
        for i, (text, expl, marks, topic_name, opts) in enumerate(questions_data):
            topic = topic_objs.get((subjects[0].id, topic_name))
            q = Question(quiz_id=q1.id, text=text, explanation=expl, marks=marks, topic_id=topic.id if topic else None, order=i)
            db.add(q)
            db.flush()
            for j, (otext, correct) in enumerate(opts):
                db.add(Option(question_id=q.id, text=otext.strip(), is_correct=correct, order=j))
        
        # Sample Quiz 2 - SQL
        q2 = Quiz(
            title="SQL Joins & Queries",
            description="Assess your understanding of SQL SELECT, JOINs and aggregations.",
            subject_id=subjects[1].id,
            difficulty=Difficulty.INTERMEDIATE,
            duration_minutes=20,
            total_marks=8,
            is_published=True,
            show_answers_after=True,
            attempt_limit=2,
            created_by_id=teacher.id
        )
        db.add(q2)
        db.flush()
        sql_qs = [
            ("Which JOIN returns only matching rows from both tables?", None, 1, "Joins",
             [("LEFT JOIN", False), ("INNER JOIN", True), ("FULL OUTER JOIN", False), ("CROSS JOIN", False)]),
            ("What does COUNT(*) return?", None, 1, "Aggregations",
             [("Number of non-null values", False), ("Number of rows", True), ("Sum of values", False), ("Average", False)]),
            ("Which clause is used to filter groups?", None, 1, "Aggregations",
             [("WHERE", False), ("HAVING", True), ("GROUP BY", False), ("ORDER BY", False)]),
            ("What is the purpose of an INDEX?", None, 1, "Indexes",
             [("To store data", False), ("To speed up queries", True), ("To enforce uniqueness only", False), ("To backup data", False)]),
            ("Which statement retrieves data?", None, 1, "SELECT Queries",
             [("GET", False), ("SELECT", True), ("FETCH", False), ("QUERY", False)]),
            ("What does PRIMARY KEY guarantee?", None, 1, "Normalization",
             [("Null values allowed", False), ("Uniqueness and not null", True), ("Fast inserts", False), ("Multiple values", False)]),
            ("LEFT JOIN returns...", None, 1, "Joins",
             [("Only matching", False), ("All from left + matching from right", True), ("All from both", False), ("Only right", False)]),
            ("Which aggregate function finds the maximum value?", None, 1, "Aggregations",
             [("MAX()", True), ("TOP()", False), ("HIGHEST()", False), ("PEAK()", False)]),
        ]
        for i, (text, expl, marks, topic_name, opts) in enumerate(sql_qs):
            topic = topic_objs.get((subjects[1].id, topic_name))
            q = Question(quiz_id=q2.id, text=text, explanation=expl, marks=marks, topic_id=topic.id if topic else None, order=i)
            db.add(q)
            db.flush()
            for j, (otext, correct) in enumerate(opts):
                db.add(Option(question_id=q.id, text=otext.strip(), is_correct=correct, order=j))
        
        # Sample Quiz 3 - Data Structures
        q3 = Quiz(
            title="Data Structures Basics",
            description="Arrays, stacks, queues and basic algorithms.",
            subject_id=subjects[2].id,
            difficulty=Difficulty.BEGINNER,
            duration_minutes=12,
            total_marks=6,
            is_published=True,
            show_answers_after=True,
            attempt_limit=3,
            created_by_id=teacher.id
        )
        db.add(q3)
        db.flush()
        ds_qs = [
            ("Which data structure uses LIFO?", None, 1, "Stacks & Queues",
             [("Queue", False), ("Stack", True), ("Array", False), ("Tree", False)]),
            ("Time complexity of accessing an array element by index?", None, 1, "Arrays & Lists",
             [("O(n)", False), ("O(1)", True), ("O(log n)", False), ("O(n log n)", False)]),
            ("Which is a FIFO structure?", None, 1, "Stacks & Queues",
             [("Stack", False), ("Queue", True), ("Heap", False), ("Graph", False)]),
            ("Binary search requires the data to be...", None, 1, "Searching",
             [("Unsorted", False), ("Sorted", True), ("Random", False), ("Hashed", False)]),
            ("What is the worst-case time for bubble sort?", None, 1, "Sorting",
             [("O(n)", False), ("O(n log n)", False), ("O(n²)", True), ("O(log n)", False)]),
            ("A tree node with no children is called a...", None, 1, "Trees",
             [("Root", False), ("Leaf", True), ("Branch", False), ("Parent", False)]),
        ]
        for i, (text, expl, marks, topic_name, opts) in enumerate(ds_qs):
            topic = topic_objs.get((subjects[2].id, topic_name))
            q = Question(quiz_id=q3.id, text=text, explanation=expl, marks=marks, topic_id=topic.id if topic else None, order=i)
            db.add(q)
            db.flush()
            for j, (otext, correct) in enumerate(opts):
                db.add(Option(question_id=q.id, text=otext.strip(), is_correct=correct, order=j))
        
        db.commit()
        print("Database seeded successfully with sample data.")
    except Exception as e:
        db.rollback()
        print(f"Seed error: {e}")
    finally:
        db.close()

# Serve frontend
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
frontend_path = os.environ.get("FRONTEND_PATH", os.path.join(_BASE, "frontend", "public"))
if os.path.isdir(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
else:
    print(f"[startup] Frontend directory not found at {frontend_path}; API-only mode.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
