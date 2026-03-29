from sqlalchemy import Column, Integer, String
from src.db.base import Base

class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    resource_code = Column(String(50), unique=True, nullable=False)
    resource_type = Column(String(20))
