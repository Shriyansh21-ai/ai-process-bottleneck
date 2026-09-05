"""Safe, read-only SQL access to the legacy analytics tables.

SECURITY NOTE
-------------
The planner (an LLM) chooses the ``table`` and an optional ``filter`` for this
tool. Both are therefore untrusted input. The previous implementation
interpolated the raw ``filter`` string straight into the WHERE clause:

    query = f"SELECT * FROM {table} WHERE {filter_clause}"

which is a textbook SQL-injection sink — a planner (or anything able to
influence the planner's input) could emit ``' OR 1=1 --``, a ``UNION SELECT``
to read arbitrary tables, comment injection, stacked statements, etc.

This module now:

  * whitelists the table (unchanged behaviour), and
  * parses ``filter`` into a small, structured grammar
    (``column <op> value`` conditions joined by ``AND``), where
      - each column is validated against a per-table whitelist,
      - each operator is validated against a fixed safe set,
      - each value is bound as a parameter (never string-interpolated).

Anything that does not fit that grammar (comments, stacked statements,
``OR 1=1``, ``UNION``, subqueries, unknown columns, unbalanced quotes, …) is
rejected with a ``ValueError`` and the query never runs. Because every value is
parameterised, even a value that *looks* like SQL is treated as a literal.

The tool is intentionally read-only (``SELECT`` only) and applies a bounded
``LIMIT`` so a broad filter cannot return an unbounded result set.
"""

import re

from sqlalchemy import text

from src.db.session import SessionLocal


# Tables the planner is permitted to query (unchanged from the original).
_ALLOWED_TABLES = {"tasks", "cases", "processes"}

# Per-table column whitelist. Only these identifiers may appear on the
# left-hand side of a filter condition. Anything else is rejected, which also
# blocks the classic ``1=1`` bypass (``1`` is not a whitelisted column).
_ALLOWED_COLUMNS = {
    "tasks": {
        "id", "task_code", "task_name", "case_id", "resource_id",
        "start_time", "end_time", "duration_minutes", "status", "created_at",
    },
    "cases": {"id", "case_code", "process_id", "created_at"},
    "processes": {"id", "process_code", "domain", "created_at"},
}

# Comparison operators the filter grammar accepts. Order matters: multi-char
# operators must be tried before their single-char prefixes.
_ALLOWED_OPERATORS = ["<=", ">=", "!=", "<>", "=", "<", ">", "LIKE", "ILIKE"]

# Maximum rows a single call may return, so a broad filter (or none) cannot pull
# an unbounded result set into memory.
_MAX_ROWS = 1000

# A single condition: <identifier> <operator> <value>. The value is captured
# loosely and validated/coerced separately (it becomes a bound parameter).
_CONDITION_RE = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*"
    r"(<=|>=|!=|<>|=|<|>|LIKE|ILIKE)\s*"
    r"(.+?)\s*$",
    re.IGNORECASE,
)


def _coerce_value(raw: str):
    """Turn a filter literal into a Python value to be BOUND as a parameter.

    Accepts a single-quoted string ('...') or a plain number. The returned
    value is only ever passed as a bound parameter, never interpolated, so the
    goal here is to reject values that are clearly not simple literals (a sign
    of an injection attempt) rather than to sanitise them.
    """
    raw = raw.strip()

    # Quoted string literal: 'abc'. Must be a single, fully-quoted token with no
    # interior single quote (an interior quote signals an injection attempt such
    # as ``'a' OR '1'='1``).
    if len(raw) >= 2 and raw[0] == "'" and raw[-1] == "'":
        inner = raw[1:-1]
        if "'" in inner:
            raise ValueError("Invalid string literal in filter")
        return inner

    # Numeric literal.
    try:
        if re.fullmatch(r"-?\d+", raw):
            return int(raw)
        if re.fullmatch(r"-?\d+\.\d+", raw):
            return float(raw)
    except ValueError:  # pragma: no cover - defensive
        pass

    raise ValueError(
        "Filter values must be a single-quoted string or a number"
    )


def _parse_filter(table: str, filter_clause: str):
    """Parse ``filter`` into a parameterised WHERE clause.

    Returns ``(where_sql, params)`` where ``where_sql`` contains only
    whitelisted column names, fixed operators and ``:pN`` placeholders, and
    ``params`` maps each placeholder to a bound value.

    Raises ``ValueError`` for anything outside the supported grammar.
    """
    allowed_columns = _ALLOWED_COLUMNS[table]

    # Reject obvious injection / multi-statement markers outright. These can
    # never appear in the supported grammar, so failing fast gives a clearer
    # error than a per-condition parse failure.
    lowered = filter_clause.lower()
    for marker in (";", "--", "/*", "*/", " union ", "(", ")"):
        if marker in lowered:
            raise ValueError("Unsupported token in filter")

    # Split on the AND conjunction only (case-insensitive, whitespace-bounded).
    # OR is intentionally unsupported: every legitimate planner filter observed
    # is a conjunction of equality/range conditions, and disallowing OR removes
    # the ``... OR 1=1`` bypass shape entirely.
    conditions = re.split(r"\s+AND\s+", filter_clause, flags=re.IGNORECASE)

    clauses = []
    params = {}

    for idx, condition in enumerate(conditions):
        match = _CONDITION_RE.match(condition)
        if not match:
            raise ValueError(f"Malformed filter condition: {condition!r}")

        column, operator, raw_value = match.groups()
        column = column.lower()
        operator = operator.upper()

        if column not in allowed_columns:
            raise ValueError(
                f"Column '{column}' is not queryable on table '{table}'"
            )
        if operator not in _ALLOWED_OPERATORS:  # pragma: no cover - regex-bound
            raise ValueError(f"Unsupported operator: {operator}")

        value = _coerce_value(raw_value)

        placeholder = f"p{idx}"
        clauses.append(f"{column} {operator} :{placeholder}")
        params[placeholder] = value

    return " AND ".join(clauses), params


def run_sql_query(input_data: dict):
    table = input_data.get("table")
    filter_clause = input_data.get("filter")

    if table not in _ALLOWED_TABLES:
        raise ValueError("Invalid table access")

    query = f"SELECT * FROM {table}"
    params = {}

    if filter_clause:
        if not isinstance(filter_clause, str):
            raise ValueError("Filter must be a string")
        where_sql, params = _parse_filter(table, filter_clause)
        query += f" WHERE {where_sql}"

    # Always bound the result set. The table name is whitelisted above.
    query += f" LIMIT {_MAX_ROWS}"

    db = SessionLocal()
    try:
        result = db.execute(text(query), params)
        rows = [dict(row._mapping) for row in result.fetchall()]
        return rows
    finally:
        db.close()
