from sqlalchemy.orm import Session
from src.models.agent_metrics import AgentMetric


def record_agent_metric(
    db: Session,
    *,
    request_id: str,
    agent_name: str,
    latency_ms: int,
    tokens_in: int = None,
    tokens_out: int = None,
    cost_usd: float = None,
    confidence: float = None,
    success: bool = True,
):
    metric = AgentMetric(
        request_id=request_id,
        agent_name=agent_name,
        latency_ms=latency_ms,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
        confidence=confidence,
        success=success,
    )
    db.add(metric)
    db.commit()
