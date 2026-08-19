"""
Registers all SQLAlchemy models on the shared Base metadata.

Importing this package ensures every table (agent_runs, step_executions,
approvals, documents, chat memory, agent tasks) is attached to
``src.db.base.Base.metadata`` for ``create_all`` and Alembic autogenerate.
"""

from src.db.models.agent_run import AgentRun
from src.db.models.agent_task import AgentTask
from src.db.models.approval import ApprovalRequest
from src.db.models.chat_memory import ChatMemory
from src.db.models.document import Document
from src.db.models.step_execution import StepExecution
from src.db.models.user import User

__all__ = [
    "AgentRun",
    "AgentTask",
    "ApprovalRequest",
    "ChatMemory",
    "Document",
    "StepExecution",
    "User",
]
