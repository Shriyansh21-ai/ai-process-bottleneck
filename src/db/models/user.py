"""
User model (Milestone 6 — authentication & user isolation).

Stores authentication identities. Passwords are NEVER stored in plaintext —
only a bcrypt hash (see ``src.core.security``). Sensitive columns
(``hashed_password``) are excluded from API responses by the response schemas
in ``src.schemas.auth``; the ORM object itself is never returned directly.
"""

from sqlalchemy import Boolean, Column, DateTime, Integer, Text
from sqlalchemy.sql import func

from src.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)

    # Unique login identifier. Case-sensitivity is handled at the app layer
    # (emails are lower-cased before storage/lookup).
    email = Column(Text, nullable=False, unique=True, index=True)

    # bcrypt hash only — never the plaintext password.
    hashed_password = Column(Text, nullable=False)

    # Disabled accounts cannot authenticate.
    is_active = Column(Boolean, nullable=False, default=True)

    # Administrative privilege. NEVER set from client input — only from the
    # database record / trusted provisioning.
    is_admin = Column(Boolean, nullable=False, default=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
