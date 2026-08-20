import os

from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL not found in environment variables"
    )

# Connection-pool + query hardening. A server-side statement_timeout ensures a
# stuck query cannot hold a pooled connection forever (the ILIKE search and any
# large scan are bounded). pool_recycle avoids stale connections; pool_timeout
# fails fast instead of blocking indefinitely when the pool is exhausted. The
# statement_timeout is PostgreSQL-specific, so it is only applied for pg URLs
# (SQLite, used in tests, does not accept it).
_engine_kwargs = dict(
    pool_pre_ping=True,
    pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
    pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
    pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
)

if DATABASE_URL.startswith("postgresql"):
    _stmt_timeout_ms = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "30000"))
    _engine_kwargs["connect_args"] = {
        "options": f"-c statement_timeout={_stmt_timeout_ms}"
    }

engine = create_engine(
    DATABASE_URL,
    **_engine_kwargs,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()