from sqlalchemy.orm import Session
from genai.tools import Tool

class DBQueryTool(Tool):
    name = "db_query"
    description = "Run read-only SQL queries for structured data"

    def __init__(self, db: Session):
        self.db = db

    def run(self, sql: str):
        result = self.db.execute(sql)
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]
