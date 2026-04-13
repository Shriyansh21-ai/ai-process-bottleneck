from sqlalchemy import text
from src.db.session import SessionLocal

def run_sql_query(input_data: dict):
    table = input_data.get("table")
    filter_clause = input_data.get("filter")

    if table not in {"tasks", "cases", "processes"}:
        raise ValueError("Invalid table access")

    query = f"SELECT * FROM {table}"
    if filter_clause:
        query += f" WHERE {filter_clause}"

    db = SessionLocal()
    try:
        result = db.execute(text(query))
        rows = [dict(row._mapping) for row in result.fetchall()]
        return rows
    finally:
        db.close()
