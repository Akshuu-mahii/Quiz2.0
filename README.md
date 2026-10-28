# SmartQuiz Analytics AI

**Online Quiz & Student Performance Analytics Platform**

Premium dark-themed educational dashboard with real authentication, quiz engine, automatic evaluation, and Python-powered performance analytics.

## Features

- **Landing page** with live platform stats
- **Role-based auth** (Student / Teacher) with JWT
- **Student dashboard** – KPIs, recent history, recommendations, trend chart
- **Online quiz interface** – timer, navigation panel, mark-for-review, auto-submit
- **Instant results** – score card, classification, answer review
- **Deep analytics** – subject/topic performance, score distribution, progress trends, personalized recommendations (Pandas + NumPy)
- **Teacher dashboard** – create/publish/delete quizzes, view class results, weak-topic identification, CSV export
- **Sample data** – 3 published quizzes (Python, SQL, Data Structures)

## Demo Accounts

| Role    | Email                   | Password    |
|---------|-------------------------|-------------|
| Student | student@smartquiz.ai    | student123  |
| Teacher | teacher@smartquiz.ai    | teacher123  |

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, SQLite, Python-Jose, Passlib, Pandas, NumPy
- **Frontend**: Vanilla JS SPA, Tailwind CSS (CDN), Chart.js, Font Awesome
- **Design**: Pure black / charcoal, purple–cyan–blue accents, glassmorphism

## Run

```bash
export PATH="$HOME/.local/bin:$PATH"
cd /home/workdir/artifacts/smartquiz
PYTHONPATH=backend python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000

Database is stored at `/tmp/smartquiz.db` (seeded on first startup if empty).

## Project Structure

```
smartquiz/
├── backend/app/
│   ├── main.py          # FastAPI routes + seed
│   ├── models.py        # SQLAlchemy models
│   ├── schemas.py       # Pydantic schemas
│   ├── auth.py          # JWT + password hashing
│   ├── analytics.py     # Pandas analytics & recommendations
│   └── database.py
├── frontend/public/
│   ├── index.html
│   └── app.js           # Full SPA
└── README.md
```

## Workflow

**Student**: Login → Dashboard → Select Quiz → Answer → Submit → Instant Results → Analytics → Recommendations

**Teacher**: Login → Create Quiz → Publish → View Results / Export CSV → Identify weak topics
