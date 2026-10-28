#!/bin/bash
cd "$(dirname "$0")"
export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"
echo "Installing dependencies (if needed)..."
pip install -q fastapi uvicorn sqlalchemy "python-jose[cryptography]" "passlib[bcrypt]" "bcrypt==4.0.1" python-multipart pandas numpy 2>/dev/null || true
echo "Starting SmartQuiz Analytics AI on http://localhost:8000"
echo "Student: student@smartquiz.ai / student123"
echo "Teacher: teacher@smartquiz.ai / teacher123"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
