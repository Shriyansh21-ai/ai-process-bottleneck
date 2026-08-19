#!/usr/bin/env python3
"""
Production smoke test for the AI Process Bottleneck API (Milestone 5).

Exercises the deployed stack end-to-end over HTTP using only the standard
library (no extra dependencies):

    * GET  /health           liveness
    * GET  /health/ready     readiness (DB + config)
    * GET  /docs             Swagger UI
    * GET  /runs/statistics  aggregate stats
    * GET  /runs             paginated list
    * POST /run              create + execute an agent run (real LLM/fallback)
    * GET  /runs/{id}        retrieve the created run

Usage:
    python scripts/smoke_test.py                       # http://localhost:8000
    python scripts/smoke_test.py --base-url http://host:8000
    python scripts/smoke_test.py --skip-run            # health/read-only only

Exit code 0 = all checks passed, non-zero = a check failed. Nothing here fakes
a successful LLM call; /run uses whatever tier the deployment has available
(OpenAI -> Ollama -> offline fallback).
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

PASS = "PASS"
FAIL = "FAIL"


def _request(method, url, payload=None, timeout=120):
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
            return resp.status, body
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


class Runner:
    def __init__(self):
        self.failures = 0

    def check(self, name, ok, detail=""):
        status = PASS if ok else FAIL
        print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))
        if not ok:
            self.failures += 1
        return ok


def main():
    parser = argparse.ArgumentParser(description="API smoke test")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--skip-run", action="store_true",
                        help="skip the POST /run agent execution check")
    parser.add_argument("--session-id", default="smoke-test")
    parser.add_argument(
        "--query",
        default="Identify the biggest bottleneck in the process.",
    )
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    r = Runner()

    # 1. liveness
    status, body = _request("GET", f"{base}/health", timeout=15)
    r.check("GET /health", status == 200 and '"healthy"' in body, f"HTTP {status}")

    # 2. readiness
    status, body = _request("GET", f"{base}/health/ready", timeout=15)
    # 200 ready; 503 not_ready is a *valid* deterministic response but a failure
    # for a production smoke test (a dependency is down).
    r.check("GET /health/ready", status == 200, f"HTTP {status} {body[:120]}")

    # 3. Swagger
    status, body = _request("GET", f"{base}/docs", timeout=15)
    r.check("GET /docs", status == 200 and "swagger" in body.lower(), f"HTTP {status}")

    # 4. statistics
    status, body = _request("GET", f"{base}/runs/statistics", timeout=30)
    r.check("GET /runs/statistics", status == 200, f"HTTP {status}")

    # 5. list runs
    status, body = _request("GET", f"{base}/runs", timeout=30)
    r.check("GET /runs", status == 200, f"HTTP {status}")

    if args.skip_run:
        print("\n(--skip-run) skipping agent execution checks")
        return 0 if r.failures == 0 else 1

    # 6. create + execute a run
    t0 = time.time()
    status, body = _request(
        "POST", f"{base}/run",
        payload={"query": args.query, "session_id": args.session_id},
        timeout=300,
    )
    took = time.time() - t0
    ran_ok = r.check("POST /run", status == 200, f"HTTP {status} in {took:.1f}s")

    # 7. verify the run was persisted and is retrievable
    if ran_ok:
        status, body = _request(
            "GET", f"{base}/runs/session/{args.session_id}", timeout=30
        )
        found = False
        if status == 200:
            try:
                found = len(json.loads(body).get("items", [])) > 0
            except (ValueError, AttributeError):
                found = False
        r.check("GET /runs/session/{id} (run persisted)", found,
                f"HTTP {status}")

    print()
    if r.failures:
        print(f"SMOKE TEST FAILED: {r.failures} check(s) failed")
        return 1
    print("SMOKE TEST PASSED: all checks green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
