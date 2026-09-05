"""Regression tests for the SQL-injection fix in ``src/tools/sql_tool.py``.

The ``run_sql_query`` tool receives its ``table``/``filter`` from an LLM planner
and therefore treats both as untrusted. These tests assert that:

  * legitimate structured filters still work and return the right rows,
  * every value is bound as a parameter (a value that looks like SQL is treated
    as a literal, not executed),
  * classic injection payloads are rejected before any query runs, and
  * only whitelisted tables and columns are queryable.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.db.base import Base
import src.models  # noqa: F401 - register legacy tables (tasks/cases/processes)
from src.models.task import Task
import src.tools.sql_tool as sql_tool


@pytest.fixture
def sql_db(monkeypatch):
    """In-memory SQLite with the legacy tables, wired into the tool.

    The tool imports ``SessionLocal`` at module scope and opens its own
    session, so we patch that symbol to point at the test database.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)

    db = TestSession()
    db.add_all([
        Task(id=1, task_code="T1", task_name="alpha",
             duration_minutes=10.0, status="success"),
        Task(id=2, task_code="T2", task_name="beta",
             duration_minutes=90.0, status="fail"),
        Task(id=3, task_code="T3", task_name="gamma",
             duration_minutes=45.0, status="rework"),
    ])
    db.commit()
    db.close()

    monkeypatch.setattr(sql_tool, "SessionLocal", TestSession)
    return TestSession


# --------------------------------------------------------------------------
# Legitimate usage still works
# --------------------------------------------------------------------------

def test_no_filter_returns_all_rows(sql_db):
    rows = sql_tool.run_sql_query({"table": "tasks"})
    assert len(rows) == 3


def test_equality_filter_string(sql_db):
    rows = sql_tool.run_sql_query({"table": "tasks", "filter": "status = 'fail'"})
    assert len(rows) == 1
    assert rows[0]["task_code"] == "T2"


def test_numeric_range_filter(sql_db):
    rows = sql_tool.run_sql_query(
        {"table": "tasks", "filter": "duration_minutes > 40"}
    )
    assert {r["task_code"] for r in rows} == {"T2", "T3"}


def test_conjunction_filter(sql_db):
    rows = sql_tool.run_sql_query(
        {"table": "tasks",
         "filter": "duration_minutes >= 40 AND status = 'rework'"}
    )
    assert len(rows) == 1
    assert rows[0]["task_code"] == "T3"


def test_like_filter(sql_db):
    rows = sql_tool.run_sql_query(
        {"table": "tasks", "filter": "task_name LIKE 'alph%'"}
    )
    assert len(rows) == 1
    assert rows[0]["task_name"] == "alpha"


# --------------------------------------------------------------------------
# Injection payloads are rejected (and never leak data)
# --------------------------------------------------------------------------

@pytest.mark.parametrize("payload", [
    "1=1 --",
    "' OR 1=1 --",
    "status = 'x' OR 1=1",
    "'; DROP TABLE tasks; --",
    "1=1; DELETE FROM tasks",
    "status = 'x' UNION SELECT * FROM users",
    "status = 'x' /* comment */",
    "id IN (SELECT id FROM users)",
    "status = 'a' OR '1'='1'",
])
def test_injection_payloads_rejected(sql_db, payload):
    with pytest.raises(ValueError):
        sql_tool.run_sql_query({"table": "tasks", "filter": payload})

    # The table is still intact and untouched after a rejected filter.
    rows = sql_tool.run_sql_query({"table": "tasks"})
    assert len(rows) == 3


def test_injection_value_treated_as_literal(sql_db):
    """A value that *looks* like SQL is bound as a parameter, not executed."""
    # This is a syntactically valid filter: column, operator, quoted literal.
    # The literal contains SQL keywords but is compared as text, so it simply
    # matches no rows instead of dropping the table or bypassing the filter.
    rows = sql_tool.run_sql_query(
        {"table": "tasks", "filter": "task_name = 'DROP TABLE tasks'"}
    )
    assert rows == []
    # Table untouched.
    assert len(sql_tool.run_sql_query({"table": "tasks"})) == 3


def test_unknown_column_rejected(sql_db):
    with pytest.raises(ValueError):
        sql_tool.run_sql_query(
            {"table": "tasks", "filter": "hacked_column = 'x'"}
        )


def test_column_from_other_table_rejected(sql_db):
    # ``domain`` exists on ``processes`` but not on ``tasks``.
    with pytest.raises(ValueError):
        sql_tool.run_sql_query(
            {"table": "tasks", "filter": "domain = 'finance'"}
        )


def test_invalid_table_rejected(sql_db):
    with pytest.raises(ValueError, match="Invalid table access"):
        sql_tool.run_sql_query({"table": "users", "filter": "id = 1"})


def test_non_string_filter_rejected(sql_db):
    with pytest.raises(ValueError):
        sql_tool.run_sql_query({"table": "tasks", "filter": {"id": 1}})
