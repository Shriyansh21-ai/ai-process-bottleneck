"""
Tests for the AgentRun management / reporting API.

Covers listing, retrieval, filtering, pagination, statistics, search,
summary vs detail shape, empty database and invalid parameters.
"""


# ------------------------------------------------------------------
# 1. List all runs
# ------------------------------------------------------------------

def test_get_all_runs(client, seeded):
    resp = client.get("/runs")
    assert resp.status_code == 200

    body = resp.json()
    assert body["total"] == len(seeded)
    assert len(body["items"]) == len(seeded)
    assert body["page"] == 1
    assert body["has_prev"] is False


# ------------------------------------------------------------------
# 2. Get run by id
# ------------------------------------------------------------------

def test_get_run_by_id(client, seeded):
    target = seeded[0]
    resp = client.get(f"/runs/{target.id}")
    assert resp.status_code == 200

    body = resp.json()
    assert body["run_id"] == target.id
    assert body["session_id"] == "alpha"
    # Detail parses stored JSON back into structured objects.
    assert body["plan"] == {"steps": [{"tool": "sql"}, {"tool": "ml"}]}
    assert body["execution_result"] == {"results": [1, 2, 3]}


# ------------------------------------------------------------------
# 3. Run not found
# ------------------------------------------------------------------

def test_run_not_found(client, seeded):
    resp = client.get("/runs/999999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ------------------------------------------------------------------
# 4. Session filtering
# ------------------------------------------------------------------

def test_session_filtering(client, seeded):
    resp = client.get("/runs/session/alpha")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert all(i["session_id"] == "alpha" for i in body["items"])


def test_session_filtering_via_query(client, seeded):
    resp = client.get("/runs", params={"session_id": "beta"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


# ------------------------------------------------------------------
# 5. Status filtering
# ------------------------------------------------------------------

def test_status_filtering(client, seeded):
    resp = client.get("/runs/status/success")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert all(i["status"] == "success" for i in body["items"])


def test_status_filtering_invalid(client, seeded):
    resp = client.get("/runs/status/not-a-status")
    assert resp.status_code == 400


# ------------------------------------------------------------------
# 6. Pagination
# ------------------------------------------------------------------

def test_pagination(client, seeded):
    page1 = client.get("/runs", params={"page": 1, "page_size": 2}).json()
    assert len(page1["items"]) == 2
    assert page1["total"] == 5
    assert page1["total_pages"] == 3
    assert page1["has_next"] is True
    assert page1["has_prev"] is False

    page3 = client.get("/runs", params={"page": 3, "page_size": 2}).json()
    assert len(page3["items"]) == 1
    assert page3["has_next"] is False
    assert page3["has_prev"] is True

    # Pages must not overlap.
    ids1 = {i["run_id"] for i in page1["items"]}
    ids3 = {i["run_id"] for i in page3["items"]}
    assert ids1.isdisjoint(ids3)


# ------------------------------------------------------------------
# 7. Statistics
# ------------------------------------------------------------------

def test_statistics(client, seeded):
    resp = client.get("/runs/statistics")
    assert resp.status_code == 200
    stats = resp.json()

    assert stats["total_runs"] == 5
    assert stats["successful_runs"] == 2
    assert stats["failed_runs"] == 1
    assert stats["running_runs"] == 1
    assert stats["success_rate"] == 40.0
    assert stats["failure_rate"] == 20.0
    # Average across the 3 runs that recorded a positive duration.
    assert stats["average_duration_ms"] == round((1200 + 800 + 400) / 3, 2)


# ------------------------------------------------------------------
# 8. Search / filtering
# ------------------------------------------------------------------

def test_search(client, seeded):
    resp = client.get("/runs/search", params={"q": "currency"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert "currency" in body["items"][0]["user_query"].lower()


def test_search_case_insensitive_via_list(client, seeded):
    resp = client.get("/runs", params={"q": "PREDICT"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_search_requires_term(client, seeded):
    resp = client.get("/runs/search")
    assert resp.status_code == 422  # missing required q


# ------------------------------------------------------------------
# 9. Summary response shape
# ------------------------------------------------------------------

def test_summary_shape(client, seeded):
    item = client.get("/runs").json()["items"][0]

    expected_keys = {
        "run_id",
        "session_id",
        "user_query",
        "status",
        "created_at",
        "started_at",
        "completed_at",
        "steps_total",
        "execution_duration_ms",
        "retry_count",
        "confidence",
        "approved",
        "verification_status",
    }
    assert expected_keys == set(item.keys())
    # Summaries must NOT leak heavy payloads.
    assert "plan" not in item
    assert "execution_result" not in item


# ------------------------------------------------------------------
# 10. Detailed response shape
# ------------------------------------------------------------------

def test_detail_shape(client, seeded):
    run = seeded[0]
    body = client.get(f"/runs/{run.id}").json()

    for key in (
        "plan",
        "execution_result",
        "verification_result",
        "steps_success",
        "steps_failed",
        "tools_used",
        "execution_mode",
        "confidence",
    ):
        assert key in body

    assert body["verification_result"] == {"approved": True, "confidence": 0.9}


def test_detail_handles_null_json(client, db_session, run_factory):
    run = run_factory(status="running", plan=None, execution_result=None)
    db_session.add(run)
    db_session.commit()

    body = client.get(f"/runs/{run.id}").json()
    assert body["plan"] is None
    assert body["execution_result"] is None


# ------------------------------------------------------------------
# 11. Empty database
# ------------------------------------------------------------------

def test_empty_database_list(client, db_session):
    body = client.get("/runs").json()
    assert body["total"] == 0
    assert body["items"] == []
    assert body["total_pages"] == 0


def test_empty_database_statistics(client, db_session):
    stats = client.get("/runs/statistics").json()
    assert stats["total_runs"] == 0
    assert stats["success_rate"] == 0.0
    assert stats["failure_rate"] == 0.0
    assert stats["average_duration_ms"] is None


# ------------------------------------------------------------------
# 12. Invalid parameters
# ------------------------------------------------------------------

def test_invalid_pagination_zero_page(client, seeded):
    assert client.get("/runs", params={"page": 0}).status_code == 422


def test_invalid_pagination_page_size_too_large(client, seeded):
    assert client.get("/runs", params={"page_size": 1000}).status_code == 422


def test_invalid_status_query(client, seeded):
    resp = client.get("/runs", params={"status": "bogus"})
    assert resp.status_code == 400
