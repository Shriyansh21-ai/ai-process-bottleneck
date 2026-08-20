"""
Tests for the additive per-run execution-steps endpoint:

    GET /runs/{run_id}/steps

Covers ordering, payload truncation, empty steps, 404 for a missing run and
owner-scoping (a user cannot read another user's run steps — no IDOR).
"""

from tests.conftest import make_run, make_step, register_and_login, user_id_for


# ------------------------------------------------------------------
# 1. Steps are returned oldest-first with truncated summaries
# ------------------------------------------------------------------

def test_steps_ordered_and_summarized(client, db_session):
    run = make_run(session_id="s1", status="success")
    db_session.add(run)
    db_session.commit()

    long_output = "x" * 2000
    db_session.add_all([
        make_step(run.id, step_id=2, tool_name="ml_analysis", status="success"),
        make_step(run.id, step_id=1, tool_name="rag_retrieval", status="success"),
    ])
    # A failed step with a long payload + error.
    failed = make_step(
        run.id, step_id=3, tool_name="predict", status="failed",
        error="model timeout", execution_time_ms=450, retry_count=2,
    )
    failed.output_payload = long_output
    db_session.add(failed)
    db_session.commit()

    resp = client.get(f"/runs/{run.id}/steps")
    assert resp.status_code == 200
    steps = resp.json()
    assert [s["step_id"] for s in steps] == [1, 2, 3]

    last = steps[-1]
    assert last["tool_name"] == "predict"
    assert last["status"] == "failed"
    assert last["error"] == "model timeout"
    assert last["retry_count"] == 2
    assert last["execution_time_ms"] == 450
    # Long payloads are truncated with an ellipsis rather than streamed whole.
    assert last["output_summary"].endswith("…")
    assert len(last["output_summary"]) < len(long_output)


# ------------------------------------------------------------------
# 2. A run with no steps yields an empty list (not an error)
# ------------------------------------------------------------------

def test_steps_empty(client, db_session):
    run = make_run(status="running")
    db_session.add(run)
    db_session.commit()

    resp = client.get(f"/runs/{run.id}/steps")
    assert resp.status_code == 200
    assert resp.json() == []


# ------------------------------------------------------------------
# 3. Missing run -> 404
# ------------------------------------------------------------------

def test_steps_run_not_found(client, db_session):
    resp = client.get("/runs/999999/steps")
    assert resp.status_code == 404


# ------------------------------------------------------------------
# 4. Owner scoping — a user cannot read another user's run steps
# ------------------------------------------------------------------

def test_steps_owner_scoped(auth_client, db_session):
    alice = register_and_login(auth_client, "alice_steps@example.com")
    register_and_login(auth_client, "bob_steps@example.com")
    bob_id = user_id_for("bob_steps@example.com")

    # A run owned by Bob, with a step.
    run = make_run(session_id="bob-s", status="success", user_id=bob_id)
    db_session.add(run)
    db_session.commit()
    db_session.add(make_step(run.id, step_id=1, tool_name="ml_analysis"))
    db_session.commit()

    # Alice must not see Bob's run steps — treated as not found.
    resp = auth_client.get(f"/runs/{run.id}/steps", headers=alice)
    assert resp.status_code == 404


# ------------------------------------------------------------------
# 5. Requires authentication
# ------------------------------------------------------------------

def test_steps_requires_auth(auth_client, db_session):
    run = make_run(status="success")
    db_session.add(run)
    db_session.commit()
    resp = auth_client.get(f"/runs/{run.id}/steps")
    assert resp.status_code == 401
