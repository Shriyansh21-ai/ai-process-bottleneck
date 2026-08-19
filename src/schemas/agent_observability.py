"""
Pydantic v2 response schemas for the Agent Observability layer.

These expose ONLY aggregated / controlled telemetry. They never carry raw
plan / execution_result / verification_result payloads or tool input/output,
so no sensitive execution data is leaked through the observability API.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class AgentHealthSummary(BaseModel):
    """Overall execution health for the selected window."""

    total_runs: int
    successful_runs: int
    failed_runs: int
    running_runs: int

    success_rate: float = Field(..., description="Successful runs as a %")
    failure_rate: float = Field(..., description="Failed runs as a %")
    approval_rate: float = Field(
        ..., description="Approved runs as a % of runs that were verified"
    )

    average_duration_ms: Optional[float] = None
    average_confidence: Optional[float] = None

    total_steps: int
    successful_steps: int
    failed_steps: int
    total_retries: int

    health_score: int = Field(..., ge=0, le=100)
    health_status: str = Field(
        ..., description="no_data | unhealthy | degraded | healthy | excellent"
    )


class ToolPerformanceSummary(BaseModel):
    """Aggregated performance for a single tool."""

    tool_name: str
    execution_count: int
    success_count: int
    failure_count: int
    success_rate: float
    average_duration_ms: Optional[float] = None
    total_retries: int


class FailureSummary(BaseModel):
    """A grouped failure reason and its share of all failures."""

    failure_type: str = Field(..., description="Failure reason / failing tool")
    count: int
    percentage: float


class ExecutionTrendPoint(BaseModel):
    """One time bucket in an execution trend series."""

    bucket: str = Field(..., description="Date bucket (YYYY-MM-DD)")
    total_runs: int
    successful_runs: int
    failed_runs: int
    average_duration_ms: Optional[float] = None
    average_confidence: Optional[float] = None


class AgentObservabilityResponse(BaseModel):
    """Combined production dashboard payload."""

    health: AgentHealthSummary
    tools: List[ToolPerformanceSummary]
    failures: List[FailureSummary]
    trends: List[ExecutionTrendPoint]
