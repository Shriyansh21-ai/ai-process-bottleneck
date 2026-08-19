"""users table + agent_runs.user_id ownership

Milestone 6 — authentication & user isolation.

Creates the ``users`` table and adds a NULLABLE ``agent_runs.user_id`` foreign
key so runs can be owned by an authenticated user.

Safe-for-existing-data strategy:
  * ``user_id`` is added as NULLABLE (never NOT NULL on a populated table).
    Pre-existing runs keep ``user_id = NULL`` and are treated as "unowned"
    (visible only to admins) — no existing row is modified or destroyed.
  * The FK uses ``ON DELETE SET NULL`` so deleting a user never cascades away
    their run history / audit trail.
  * Idempotent: the table / column / index / FK are each created only if absent
    and dropped only if present, so the migration is re-runnable.

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-08-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, Sequence[str], None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FK_NAME = "fk_agent_runs_user_id_users"
IX_NAME = "ix_agent_runs_user_id"


def _tables(insp):
    return set(insp.get_table_names())


def _columns(insp, table):
    if table not in _tables(insp):
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def _indexes(insp, table):
    if table not in _tables(insp):
        return set()
    return {ix["name"] for ix in insp.get_indexes(table)}


def _fks(insp, table):
    if table not in _tables(insp):
        return set()
    return {fk.get("name") for fk in insp.get_foreign_keys(table)}


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    # --- users table ---
    if "users" not in _tables(insp):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("email", sa.Text(), nullable=False),
            sa.Column("hashed_password", sa.Text(), nullable=False),
            sa.Column(
                "is_active", sa.Boolean(), nullable=False,
                server_default=sa.true(),
            ),
            sa.Column(
                "is_admin", sa.Boolean(), nullable=False,
                server_default=sa.false(),
            ),
            sa.Column(
                "created_at", sa.DateTime(timezone=True),
                server_default=sa.func.now(), nullable=False,
            ),
            sa.Column(
                "updated_at", sa.DateTime(timezone=True),
                server_default=sa.func.now(), nullable=False,
            ),
        )
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    # --- agent_runs.user_id (nullable) ---
    if "agent_runs" in _tables(insp):
        if "user_id" not in _columns(insp, "agent_runs"):
            op.add_column(
                "agent_runs",
                sa.Column("user_id", sa.Integer(), nullable=True),
            )
        if IX_NAME not in _indexes(insp, "agent_runs"):
            op.create_index(IX_NAME, "agent_runs", ["user_id"])
        # SQLite cannot ALTER TABLE ADD CONSTRAINT; the FK is only added on
        # servers that support it (PostgreSQL). Ownership filtering does not
        # depend on the DB-level FK.
        if not is_sqlite and FK_NAME not in _fks(insp, "agent_runs"):
            op.create_foreign_key(
                FK_NAME, "agent_runs", "users",
                ["user_id"], ["id"], ondelete="SET NULL",
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    if "agent_runs" in _tables(insp):
        if not is_sqlite and FK_NAME in _fks(insp, "agent_runs"):
            op.drop_constraint(FK_NAME, "agent_runs", type_="foreignkey")
        if IX_NAME in _indexes(insp, "agent_runs"):
            op.drop_index(IX_NAME, table_name="agent_runs")
        if "user_id" in _columns(insp, "agent_runs"):
            op.drop_column("agent_runs", "user_id")

    if "users" in _tables(insp):
        if "ix_users_email" in _indexes(insp, "users"):
            op.drop_index("ix_users_email", table_name="users")
        op.drop_table("users")
