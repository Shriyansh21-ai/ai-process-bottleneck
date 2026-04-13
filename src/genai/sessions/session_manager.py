from sqlalchemy.orm import Session
from src.models.genai_session import GenAISession

class SessionManager:

    def __init__(self, db: Session):
        self.db = db

    def create_session(self) -> GenAISession:
        session = GenAISession()
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session(self, session_id: str) -> GenAISession | None:
        return (
            self.db.query(GenAISession)
            .filter(GenAISession.id == session_id)
            .first()
        )

    def touch_session(self, session_id: str):
        session = self.get_session(session_id)
        if session:
            self.db.commit()
