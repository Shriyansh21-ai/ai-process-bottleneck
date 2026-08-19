"""
Milestone 3 tests — agent observability & execution analytics.

Deterministic, SQLite-only (no Postgres / OpenAI / Qdrant / network).
Covers health, tool performance, failures, trends, the health score and the
/observability API, plus backward-compat of the existing /runs endpoints.
"""

from datetime import datetime

import pytest

from src.services.agent_observability_service import (
    compute_health_score,
    get_agent_health,
    get_execution_trends,
    get_failure_summary,
    get_tool_performance,
)


# ------------------------------------------------------------------
# seed helpers
# ------------------------------------------------------------------

def _run(db, run_factory, **kwargs):
    run = run_factory(**kwargs)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _steps(db, step_factory, run_id, specs):
    """specs: list of dicts with tool/status/[error,ms,retries]."""
    for i, spec in enumerate(specs, start=1):
        db.add(
            step_factory(
                run_id,
                step_id=i,
                tool_name=spec["tool"],
                status=spec.get("status", "success"),
                error=spec.get("error"),
                execution_time_ms=spec.get("ms", 100),
                retry_count=spec.get("retries", 0),
            )
        )
    db.commit()


# ==================================================================
# HEALTH
# ==================================================================

def test_health_empty_db(db_session):
    h = get_agent_health(db_session)
    assert h["total_runs"] == 0
    assert h["success_rate"] == 0.0
    assert h["failure_rate"] == 0.0
    assert h["approval_rate"] == 0.0
    assert h["average_duration_ms"] is None
    assert h["average_confidence"] is None
    assert h["health_score"] == 0
    assert h["health_status"] == "no_data"


def test_health_all_successful(db_session, run_factory):
    for _ in range(3):
        _run(
            db_session, run_factory,
            status="completed", approved=True, confidence=0.9,
            duration_ms=200, steps_total=3, steps_success=3, steps_failed=0,
            retry_count=0,
        )
    h = get_agent_health(db_session)
    assert h["total_runs"] == 3
    assert h["successful_runs"] == 3
    assert h["failed_runs"] == 0
    assert h["success_rate"] == 100.0
    assert h["failure_rate"] == 0.0
    assert h["health_status"] == "excellent"


def test_health_mixed(db_session, run_factory):
    _run(db_session, run_factory, status="completed", approved=True)
    _run(db_session, run_factory, status="completed", approved=True)
    _run(db_session, run_factory, status="failed", approved=False)
    h = get_agent_health(db_session)
    assert h["total_runs"] == 3
    assert h["successful_runs"] == 2
    assert h["failed_runs"] == 1
    assert h["success_rate"] == 66.67
    assert h["failure_rate"] == 33.33


def test_health_running_counted(db_session, run_factory):
    _run(db_session, run_factory, status="running")
    _run(db_session, run_factory, status="completed")
    h = get_agent_health(db_session)
    assert h["running_runs"] == 1


def test_health_duration_average_ignores_zero(db_session, run_factory):
    _run(db_session, run_factory, status="completed", duration_ms=100)
    _run(db_session, run_factory, status="completed", duration_ms=300)
    _run(db_session, run_factory, status="completed", duration_ms=0)
    h = get_agent_health(db_session)
    assert h["average_duration_ms"] == 200.0


def test_health_confidence_average(db_session, run_factory):
    _run(db_session, run_factory, status="completed", confidence=0.8)
    _run(db_session, run_factory, status="completed", confidence=0.9)
    h = get_agent_health(db_session)
    assert h["average_confidence"] == 0.85


def test_health_approval_rate_excludes_unverified(db_session, run_factory):
    _run(db_session, run_factory, status="completed", approved=True)
    _run(db_session, run_factory, status="completed", approved=True)
    _run(db_session, run_factory, status="completed", approved=False)
    _run(db_session, run_factory, status="completed", approved=None)
    h = get_agent_health(db_session)
    # 2 approved out of 3 verified runs.
    assert h["approval_rate"] == 66.67


def test_health_step_and_retry_totals(db_session, run_factory):
    _run(
        db_session, run_factory, status="completed",
        steps_total=3, steps_success=2, steps_failed=1, retry_count=2,
    )
    _run(
        db_session, run_factory, status="completed",
        steps_total=1, steps_success=1, steps_failed=0, retry_count=3,
    )
    h = get_agent_health(db_session)
    assert h["total_steps"] == 4
    assert h["successful_steps"] == 3
    assert h["failed_steps"] == 1
    assert h["total_retries"] == 5


def test_health_session_filter(db_session, run_factory):
    _run(db_session, run_factory, session_id="a", status="completed")
    _run(db_session, run_factory, session_id="b", status="failed")
    h = get_agent_health(db_session, session_id="a")
    assert h["total_runs"] == 1
    assert h["successful_runs"] == 1


# ==================================================================
# TOOL PERFORMANCE
# ==================================================================

def test_tool_performance_multiple(db_session, run_factory, step_factory):
    run = _run(db_session, run_factory, status="completed")
    _steps(
        db_session, step_factory, run.id,
        [
            {"tool": "ml_analysis", "status": "success", "ms": 100},
            {"tool": "ml_analysis", "status": "success", "ms": 300},
            {"tool": "rag_retrieval", "status": "success", "ms": 50},
            {"tool": "rag_retrieval", "status": "failed", "ms": 20,
             "retries": 2},
            {"tool": "sql_query", "status": "failed", "ms": 10, "retries": 1},
        ],
    )
    perf = {t["tool_name"]: t for t in get_tool_performance(db_session)}

    assert perf["ml_analysis"]["execution_count"] == 2
    assert perf["ml_analysis"]["success_count"] == 2
    assert perf["ml_analysis"]["success_rate"] == 100.0
    assert perf["ml_analysis"]["average_duration_ms"] == 200.0

    assert perf["rag_retrieval"]["execution_count"] == 2
    assert perf["rag_retrieval"]["failure_count"] == 1
    assert perf["rag_retrieval"]["success_rate"] == 50.0
    assert perf["rag_retrieval"]["total_retries"] == 2

    assert perf["sql_query"]["failure_count"] == 1
    assert perf["sql_query"]["total_retries"] == 1


def test_tool_performance_ordering_most_used_first(
    db_session, run_factory, step_factory
):
    run = _run(db_session, run_factory, status="completed")
    _steps(
        db_session, step_factory, run.id,
        [
            {"tool": "ml_analysis"},
            {"tool": "ml_analysis"},
            {"tool": "ml_analysis"},
            {"tool": "rag_retrieval"},
        ],
    )
    perf = get_tool_performance(db_session)
    assert perf[0]["tool_name"] == "ml_analysis"
    assert perf[0]["execution_count"] == 3


def test_tool_performance_filter_by_tool(
    db_session, run_factory, step_factory
):
    run = _run(db_session, run_factory, status="completed")
    _steps(
        db_session, step_factory, run.id,
        [{"tool": "ml_analysis"}, {"tool": "rag_retrieval"}],
    )
    perf = get_tool_performance(db_session, tool_name="rag_retrieval")
    assert len(perf) == 1
    assert perf[0]["tool_name"] == "rag_retrieval"


def test_tool_performance_empty(db_session):
    assert get_tool_performance(db_session) == []


# ==================================================================
# FAILURES
# ==================================================================

def test_failure_summary_multiple_reasons(
    db_session, run_factory, step_factory
):
    run = _run(db_session, run_factory, status="failed")
    _steps(
        db_session, step_factory, run.id,
        [
            {"tool": "sql_query", "status": "failed", "error": "timeout"},
            {"tool": "sql_query", "status": "failed", "error": "timeout"},
            {"tool": "rag_retrieval", "status": "failed",
             "error": "connection refused"},
            {"tool": "ml_analysis", "status": "success"},
        ],
    )
    failures = get_failure_summary(db_session)
    by_reason = {f["failure_type"]: f for f in failures}

    assert by_reason["timeout"]["count"] == 2
    assert by_reason["connection refused"]["count"] == 1
    # Only failed steps counted (the successful ml step is excluded).
    assert sum(f["count"] for f in failures) == 3
    assert by_reason["timeout"]["percentage"] == 66.67


def test_failure_summary_empty(db_session, run_factory, step_factory):
    run = _run(db_session, run_factory, status="completed")
    _steps(db_session, step_factory, run.id, [{"tool": "ml_analysis"}])
    assert get_failure_summary(db_session) == []


def test_failure_summary_null_error(db_session, run_factory, step_factory):
    run = _run(db_session, run_factory, status="failed")
    _steps(
        db_session, step_factory, run.id,
        [{"tool": "web_search", "status": "failed", "error": None}],
    )
    failures = get_failure_summary(db_session)
    assert failures[0]["failure_type"] == "web_search: unknown error"
    assert failures[0]["percentage"] == 100.0


# ==================================================================
# TRENDS
# ==================================================================

def test_trends_grouping_by_date(db_session, run_factory):
    _run(db_session, run_factory, status="completed",
         created_at=datetime(2026, 8, 10, 9, 0, 0))
    _run(db_session, run_factory, status="failed",
         created_at=datetime(2026, 8, 10, 15, 0, 0))
    _run(db_session, run_factory, status="completed",
         created_at=datetime(2026, 8, 11, 10, 0, 0))

    trends = get_execution_trends(db_session)
    assert [t["bucket"] for t in trends] == ["2026-08-10", "2026-08-11"]

    day1 = trends[0]
    assert day1["total_runs"] == 2
    assert day1["successful_runs"] == 1
    assert day1["failed_runs"] == 1


def test_trends_date_filter(db_session, run_factory):
    _run(db_session, run_factory, status="completed",
         created_at=datetime(2026, 8, 1, 9, 0, 0))
    _run(db_session, run_factory, status="completed",
         created_at=datetime(2026, 8, 15, 9, 0, 0))

    trends = get_execution_trends(
        db_session, start_date=datetime(2026, 8, 10)
    )
    assert len(trends) == 1
    assert trends[0]["bucket"] == "2026-08-15"


def test_trends_averages(db_session, run_factory):
    _run(db_session, run_factory, status="completed", duration_ms=100,
         confidence=0.8, created_at=datetime(2026, 8, 10, 9, 0, 0))
    _run(db_session, run_factory, status="completed", duration_ms=300,
         confidence=0.9, created_at=datetime(2026, 8, 10, 10, 0, 0))
    trends = get_execution_trends(db_session)
    assert trends[0]["average_duration_ms"] == 200.0
    assert trends[0]["average_confidence"] == 0.85


# ==================================================================
# HEALTH SCORE (pure, deterministic)
# ==================================================================

def _metrics(**overrides):
    base = {
        "total_runs": 10,
        "success_rate": 100.0,
        "approval_rate": 100.0,
        "average_confidence": 1.0,
        "total_steps": 10,
        "failed_steps": 0,
        "total_retries": 0,
    }
    base.update(overrides)
    return base


def test_score_no_data():
    assert compute_health_score(_metrics(total_runs=0)) == (0, "no_data")


def test_score_excellent():
    score, status = compute_health_score(_metrics())
    assert score == 100
    assert status == "excellent"


def test_score_unhealthy():
    score, status = compute_health_score(
        _metrics(
            success_rate=5.0, approval_rate=0.0, average_confidence=0.1,
            total_steps=10, failed_steps=9, total_retries=50,
        )
    )
    assert score < 40
    assert status == "unhealthy"


def test_score_degraded():
    score, status = compute_health_score(
        _metrics(
            success_rate=55.0, approval_rate=50.0, average_confidence=0.5,
            total_steps=10, failed_steps=3, total_retries=5,
        )
    )
    assert 40 <= score < 70
    assert status == "degraded"


def test_score_healthy():
    score, status = compute_health_score(
        _metrics(
            success_rate=80.0, approval_rate=80.0, average_confidence=0.8,
            total_steps=10, failed_steps=1, total_retries=1,
        )
    )
    assert 70 <= score < 85
    assert status == "healthy"


def test_score_missing_confidence_is_neutral():
    with_conf = compute_health_score(_metrics(average_confidence=0.7))
    without_conf = compute_health_score(_metrics(average_confidence=None))
    # Missing confidence is treated as neutral 0.70.
    assert with_conf == without_conf


def test_score_deterministic():
    m = _metrics(success_rate=73.0, average_confidence=0.66, total_retries=4)
    assert compute_health_score(m) == compute_health_score(m)


# ==================================================================
# API
# ==================================================================

def test_api_health_200(obs_client, db_session, run_factory):
    _run(db_session, run_factory, status="completed", approved=True,
         confidence=0.9, duration_ms=100, steps_total=1, steps_success=1)
    resp = obs_client.get("/observability/health")
    assert resp.status_code == 200
    body = resp.json()
    for key in (
        "total_runs", "success_rate", "failure_rate", "approval_rate",
        "average_duration_ms", "average_confidence", "total_steps",
        "total_retries", "health_score", "health_status",
    ):
        assert key in body
    assert body["total_runs"] == 1


def test_api_tools_200(obs_client, db_session, run_factory, step_factory):
    run = _run(db_session, run_factory, status="completed")
    _steps(db_session, step_factory, run.id, [{"tool": "ml_analysis"}])
    resp = obs_client.get("/observability/tools")
    assert resp.status_code == 200
    assert resp.json()[0]["tool_name"] == "ml_analysis"


def test_api_failures_200(obs_client, db_session, run_factory, step_factory):
    run = _run(db_session, run_factory, status="failed")
    _steps(db_session, step_factory, run.id,
           [{"tool": "sql_query", "status": "failed", "error": "boom"}])
    resp = obs_client.get("/observability/failures")
    assert resp.status_code == 200
    assert resp.json()[0]["failure_type"] == "boom"


def test_api_trends_200(obs_client, db_session, run_factory):
    _run(db_session, run_factory, status="completed",
         created_at=datetime(2026, 8, 10, 9, 0, 0))
    resp = obs_client.get("/observability/trends")
    assert resp.status_code == 200
    assert resp.json()[0]["bucket"] == "2026-08-10"


def test_api_overview_200(obs_client, db_session, run_factory, step_factory):
    run = _run(db_session, run_factory, status="completed", approved=True,
               confidence=0.9)
    _steps(db_session, step_factory, run.id, [{"tool": "ml_analysis"}])
    resp = obs_client.get("/observability/overview")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"health", "tools", "failures", "trends"}
    assert body["health"]["total_runs"] == 1


def test_api_invalid_date_range_400(obs_client):
    resp = obs_client.get(
        "/observability/health",
        params={"start_date": "2026-08-15", "end_date": "2026-08-01"},
    )
    assert resp.status_code == 400


def test_api_invalid_status_400(obs_client):
    resp = obs_client.get(
        "/observability/health", params={"status": "not-real"}
    )
    assert resp.status_code == 400


def test_api_invalid_date_format_422(obs_client):
    resp = obs_client.get(
        "/observability/health", params={"start_date": "not-a-date"}
    )
    assert resp.status_code == 422


def test_api_empty_results(obs_client):
    assert obs_client.get("/observability/health").json()["health_status"] == (
        "no_data"
    )
    assert obs_client.get("/observability/tools").json() == []
    assert obs_client.get("/observability/failures").json() == []
    assert obs_client.get("/observability/trends").json() == []


# ==================================================================
# BACKWARD COMPATIBILITY
# ==================================================================

def test_existing_runs_endpoints_still_work(
    obs_client, db_session, run_factory
):
    _run(db_session, run_factory, status="completed")
    assert obs_client.get("/runs").status_code == 200
    assert obs_client.get("/runs/statistics").status_code == 200
