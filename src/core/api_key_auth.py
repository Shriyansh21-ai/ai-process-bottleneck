from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session
from src.core.security import hash_api_key
from src.db.session import SessionLocal
from sqlalchemy import text

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_api_key(
    x_api_key: str = Header(...),
    db: Session = Depends(get_db)
):
    hashed = hash_api_key(x_api_key)

    result = db.execute(
        text("""
        SELECT owner, role, is_active
        FROM api_keys
        WHERE key_hash = :hash
        """),
        {"hash": hashed}
    ).fetchone()

    if not result or not result.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key"
        )

    return {
        "owner": result.owner,
        "role": result.role,
        "auth_type": "api_key"
    }
