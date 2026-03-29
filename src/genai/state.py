from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class AgentState:
    task: str
    plan: List[str]
    context: str
    observations: List[str]
    result: str | None = None
    metadata: Dict[str, Any] = None
