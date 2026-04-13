from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.db.base import Base   # ✅ import SAME Base

DATABASE_URL = "postgresql://postgres:SHRIdev%401234@localhost:5432/ai_process"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)