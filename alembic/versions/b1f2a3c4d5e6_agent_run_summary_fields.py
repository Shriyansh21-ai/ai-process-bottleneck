"""agent run summary fields

Ensures the ``agent_runs`` table exists and carries the extended execution
summary columns (timings, step counters, confidence, etc.).

This migration is written to be SAFE and IDEMPOTENT:

  * On a fresh database it creates the full ``agent_runs`` table.
  * On an existing database (e.g. one bootstrapped via ``create_all``) it only
    adds columns that are missing. Nothing is dropped and no data is deleted.

Revision ID: b1f2a3c4d5e6
Revises: 8356b5c62964
Create Date: 2026-08-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "b1f2a3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "8356b5c62964"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE = "agent_runs"


def _core_columns():
    """Base columns that already existed on the original model."""
    return [
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("session_id", sa.Text, nullable=False),
        sa.Column("user_query", sa.Text, nullable=False),
        sa.Column("plan", sa.Text),
        sa.Column("execution_result", sa.Text),
        sa.Column("verification_result", sa.Text),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    ]


def _summary_columns():
    """New execution-summary columns – added if not already present."""
    return [
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("duration_ms", sa.Integer, server_default="0"),
        sa.Column("steps_total", sa.Integer, server_default="0"),
        sa.Column("steps_success", sa.Integer, server_default="0"),
        sa.Column("steps_failed", sa.Integer, server_default="0"),
        sa.Column("retry_count", sa.Integer, server_default="0"),
        sa.Column("tools_used", sa.JSON),
        sa.Column("execution_mode", sa.Text, server_default="parallel"),
        sa.Column("memory_used", sa.Boolean, server_default=sa.false()),
        sa.Column("rag_used", sa.Boolean, server_default=sa.false()),
        sa.Column("confidence", sa.Float),
        sa.Column("approved", sa.Boolean),
        sa.Column("llm_model", sa.Text),
        sa.Column("final_response", sa.Text),
    ]


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    if TABLE not in insp.get_table_names():
        op.create_table(
            TABLE,
            *_core_columns(),
            *_summary_columns(),
        )
        return

    existing = {c["name"] for c in insp.get_columns(TABLE)}
    for column in _summary_columns():
        if column.name not in existing:
            op.add_column(TABLE, column)


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    if TABLE not in insp.get_table_names():
        return

    existing = {c["name"] for c in insp.get_columns(TABLE)}
    # Drop only the summary columns this migration introduced; leave the
    # base table and its data intact.
    for column in _summary_columns():
        if column.name in existing:
            op.drop_column(TABLE, column.name)
