"""observability indexes

Adds indexes that materially speed up the Milestone 3 observability
aggregations (filtering agent_runs by created_at/status/session_id and
grouping/joining step_executions by agent_run_id/tool_name/status).

Safe & idempotent: each index is created only if absent and dropped only if
present. No data is touched and no existing index is removed.

Revision ID: c2d3e4f5a6b7
Revises: b1f2a3c4d5e6
Create Date: 2026-08-17

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect


revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "b1f2a3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (index_name, table_name, [columns])
INDEXES = [
    ("ix_agent_runs_created_at", "agent_runs", ["created_at"]),
    ("ix_agent_runs_status", "agent_runs", ["status"]),
    ("ix_agent_runs_session_id", "agent_runs", ["session_id"]),
    ("ix_step_executions_agent_run_id", "step_executions", ["agent_run_id"]),
    ("ix_step_executions_tool_name", "step_executions", ["tool_name"]),
    ("ix_step_executions_status", "step_executions", ["status"]),
]


def _existing(insp, table):
    if table not in insp.get_table_names():
        return set()
    return {ix["name"] for ix in insp.get_indexes(table)}


def upgrade() -> None:
    insp = inspect(op.get_bind())
    for name, table, columns in INDEXES:
        if table in insp.get_table_names() and name not in _existing(insp, table):
            op.create_index(name, table, columns)


def downgrade() -> None:
    insp = inspect(op.get_bind())
    for name, table, _columns in INDEXES:
        if name in _existing(insp, table):
            op.drop_index(name, table_name=table)
