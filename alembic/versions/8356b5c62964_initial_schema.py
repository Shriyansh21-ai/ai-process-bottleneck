"""initial schema

Baseline for the legacy analytics tables (cases / processes / resources /
tasks). Originally this migration only created a few indexes and assumed the
tables already existed (they had been bootstrapped out-of-band via
``Base.metadata.create_all``). That made ``alembic upgrade head`` fail on a
truly fresh database ("no such table: cases").

Milestone 8 fix: this migration is now SAFE and IDEMPOTENT.

  * On a fresh database it CREATES the legacy tables (via the model metadata)
    and their indexes.
  * On an existing database (bootstrapped via ``create_all``) it only adds
    whatever indexes / column tweaks are still missing.

Nothing is dropped and no data is deleted.

Revision ID: 8356b5c62964
Revises:
Create Date: 2026-01-17 19:14:10.012567

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '8356b5c62964'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_LEGACY_TABLES = ["processes", "resources", "cases", "tasks"]
_INDEXES = [
    ("ix_cases_id", "cases", "id"),
    ("ix_processes_id", "processes", "id"),
    ("ix_resources_id", "resources", "id"),
    ("ix_tasks_id", "tasks", "id"),
]


def _existing_index_names(insp, table):
    try:
        return {ix["name"] for ix in insp.get_indexes(table)}
    except Exception:
        return set()


def upgrade() -> None:
    """Upgrade schema (idempotent full baseline).

    Creates the complete application schema from the SQLAlchemy models. This is
    the authoritative baseline: it registers BOTH model packages
    (``src.models`` — legacy analytics tables — and ``src.db.models`` — agent
    runs, steps, users, etc.) and creates every table that does not already
    exist. ``create_all`` is idempotent (checkfirst=True), so on a DB that was
    bootstrapped out-of-band it is a no-op; the later migrations
    (b1f2/c2d3/d3e4) are themselves idempotent and reconcile any per-column /
    per-index drift.
    """
    bind = op.get_bind()
    insp = inspect(bind)

    # Import BOTH model packages so their tables are registered on the shared
    # metadata before we create them.
    from src.db.base import Base
    import src.models  # noqa: F401  (legacy: cases/processes/resources/tasks/...)
    import src.db.models  # noqa: F401  (agent_runs/step_executions/users/...)

    present = set(insp.get_table_names())
    tasks_preexisted = "tasks" in present

    # Create every model-defined table that is missing (fresh DB → full schema).
    Base.metadata.create_all(bind=bind)

    # Refresh inspector after creation.
    insp = inspect(bind)
    present = set(insp.get_table_names())

    # Create indexes only where the table exists and the index does not.
    for index_name, table, column in _INDEXES:
        if table in present and index_name not in _existing_index_names(insp, table):
            op.create_index(op.f(index_name), table, [column], unique=False)

    # Original column tweak: widen tasks.task_name TEXT -> String. Only needed
    # when the table pre-existed with the old TEXT type; freshly created tables
    # already use the model's String type.
    if tasks_preexisted:
        try:
            op.alter_column(
                'tasks', 'task_name',
                existing_type=sa.TEXT(),
                type_=sa.String(),
                existing_nullable=True,
            )
        except Exception:
            # Some dialects (e.g. SQLite) cannot alter column types in place;
            # the type is cosmetic here, so a failure is non-fatal.
            pass


def downgrade() -> None:
    """Downgrade schema (guarded)."""
    bind = op.get_bind()
    insp = inspect(bind)
    present = set(insp.get_table_names())

    for index_name, table, _column in _INDEXES:
        if table in present and index_name in _existing_index_names(insp, table):
            op.drop_index(op.f(index_name), table_name=table)

    if "tasks" in present:
        try:
            op.alter_column(
                'tasks', 'task_name',
                existing_type=sa.String(),
                type_=sa.TEXT(),
                existing_nullable=True,
            )
        except Exception:
            pass
