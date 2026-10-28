from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
import os

# Portable path: uses smartquiz/data/smartquiz.db next to the project
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DEFAULT_DB = os.path.join(_BASE, "data", "smartquiz.db")
os.makedirs(os.path.dirname(_DEFAULT_DB), exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{_DEFAULT_DB}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
