# AI Process Bottleneck

An AI-powered backend system for intelligent workflow automation, semantic processing, local LLM inference, and scalable AI integration.

This project is designed as a production-style AI infrastructure backend that combines:

* Semantic embeddings
* Local LLM inference using Ollama
* FastAPI backend architecture
* Vector-ready processing pipeline
* Modular AI service structure
* Offline-first AI capabilities

---

# Overview

AI Process Bottleneck is built to simulate a real-world AI infrastructure system that can:

* Process and embed text data
* Run local AI models offline
* Provide scalable API-based AI services
* Support future vector search and RAG systems
* Serve as a foundation for intelligent workflow automation

The project focuses heavily on:

* Clean architecture
* Production-ready backend structure
* Modular AI pipelines
* Local-first AI deployment
* Performance optimization

---

# Core Features

## Semantic Embeddings

Uses Sentence Transformers for high-quality semantic embeddings.

Current embedding model:

* `sentence-transformers/all-MiniLM-L6-v2`

Capabilities:

* Semantic similarity
* Text understanding
* Embedding generation
* Vector database compatibility
* RAG-ready architecture

---

## Local LLM Inference with Ollama

Integrated local AI inference using Ollama.

Current recommended model:

* `phi3:mini`

Low-RAM fallback:

* `tinyllama`

Benefits:

* Fully offline AI inference
* No API cost
* Local data privacy
* Fast local responses
* Production-ready architecture

---

## FastAPI Backend

Modern asynchronous backend architecture using FastAPI.

Features:

* Async endpoints
* Scalable structure
* High performance
* Easy API testing
* Swagger documentation
* Production deployment ready

---

## Modular AI Architecture

The project follows a clean modular structure:

```text
src/
 ├── genai/
 │    ├── embeddings/
 │    ├── offline/
 │    ├── config/
 │    ├── shared/
 │    └── model_loader.py
 │
 ├── routes/
 ├── services/
 ├── database/
 └── utils/
```

This structure allows:

* Easy scaling
* Better maintainability
* Team collaboration
* Separation of concerns
* Production-level organization

---

# Tech Stack

## Backend

* Python
* FastAPI
* Uvicorn

## AI / ML

* Sentence Transformers
* Hugging Face Transformers
* Ollama
* Local LLMs

## Database

* PostgreSQL
* SQLAlchemy

## Async & Networking

* aiohttp
* Async Python

---

# System Architecture

```text
User Request
     ↓
FastAPI Backend
     ↓
AI Processing Layer
     ├── Embedding Engine
     ├── Ollama LLM Engine
     └── Semantic Processing
     ↓
Response Generation
     ↓
API Response
```

---

# Installation

## 1. Clone Repository

```bash
git clone <your-repository-url>
cd ai-process-bottleneck
```

---

## 2. Create Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / Mac

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install Requirements

```bash
pip install -r requirements.txt
```

---

# Ollama Setup

## Install Ollama

Official Website:

* [https://ollama.com](https://ollama.com)

---

## Run Recommended Model

```bash
ollama run phi3:mini
```

If your system has low RAM:

```bash
ollama run tinyllama
```

---

# Environment Configuration

Create a `.env` file:

```env
# ============================================================
# DATABASE
# ============================================================

POSTGRES_DB=your_db_name
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password
POSTGRES_PORT=5432

# ============================================================
# MODEL PROVIDER
# ============================================================

DEFAULT_PROVIDER=ollama

# ============================================================
# OLLAMA
# ============================================================

OLLAMA_MODEL=phi3:mini
OLLAMA_BASE_URL=http://localhost:11434

# ============================================================
# OPENAI (OPTIONAL)
# ============================================================

OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
```

---

# Running the Backend

Start the FastAPI server:

```bash
python -m uvicorn main:app --reload
```

Backend will run at:

```text
http://127.0.0.1:8000
```

Swagger API docs:

```text
http://127.0.0.1:8000/docs
```

---

# Example Startup Logs

```text
✅ Embedding model loaded
✅ Ollama connected
🚀 Backend ready
```

---

# Current Capabilities

The backend currently supports:

* Embedding generation
* Local AI inference
* Async API handling
* Modular AI services
* Offline-first architecture
* Fast semantic processing

---

# Planned Features

Upcoming roadmap includes:

## Retrieval-Augmented Generation (RAG)

* Vector database integration
* Semantic document retrieval
* Context-aware AI responses

## Workflow Intelligence

* AI workflow optimization
* Bottleneck detection
* Automated recommendations

## AI Agent System

* Multi-agent orchestration
* Tool calling
* Autonomous task execution

## Vector Search

* pgvector integration
* Similarity search
* Semantic indexing

## Monitoring & Analytics

* AI performance tracking
* Request analytics
* Usage metrics

---

# Why This Project?

This project was built to explore and implement:

* Real-world AI backend engineering
* Production-grade AI system architecture
* Local AI deployment
* Scalable semantic systems
* AI infrastructure design

It is designed as both:

* A learning-focused AI infrastructure project
* A scalable foundation for future AI products

---

# Performance Focus

Key optimization areas:

* Model preloading
* Async processing
* Modular architecture
* Reduced API latency
* Offline AI execution
* Scalable backend structure

---

# Security & Privacy

Benefits of local AI execution:

* No external API dependency
* Data remains local
* Reduced operational cost
* Offline processing capability
* Better privacy control

---

# Requirements

Recommended system:

* Python 3.10+
* 8GB+ RAM recommended
* Ollama installed
* PostgreSQL installed

Minimum system:

* Python 3.10+
* 4GB RAM
* tinyllama model

---

# API Testing

You can test APIs using:

* FastAPI Swagger Docs
* Postman
* cURL
* Frontend integration

---

# Future Vision

The long-term vision for this project is to evolve into:

* AI workflow intelligence platform
* Enterprise AI orchestration system
* Autonomous AI processing engine
* Scalable AI infrastructure layer

---

# Contributing

Contributions, improvements, and feature suggestions are welcome.

Potential contribution areas:

* RAG pipelines
* Vector databases
* Agent systems
* AI orchestration
* Performance optimization
* Frontend dashboards

---

# License

This project is open-source and available under the MIT License.

---

# Author

Built with a focus on:

* AI engineering
* Backend architecture
* Local AI systems
* Scalable infrastructure
* Production-ready development

---

# Production Hardening, Observability & Reliability (Milestone 4)

This milestone hardens the existing agent system for production without changing
its core execution behaviour.

## Health & Readiness

| Endpoint | Purpose | Responses |
| --- | --- | --- |
| `GET /health` | Liveness — the process is up | `200 {"status":"healthy", ...}` |
| `GET /health/ready` | Readiness — critical dependencies OK | `200 {"status":"ready","checks":{...}}` / `503 {"status":"not_ready","checks":{"database":"unavailable"}}` |

Readiness checks PostgreSQL connectivity and that required configuration is
present. Connection strings and credentials are never exposed.

## Request / Agent Correlation

Every request is assigned a `request_id` (a valid inbound `X-Request-ID` header
is honoured, otherwise a UUID4 is generated). It is returned in the
`X-Request-ID` response header and included in logs, enabling end-to-end
tracing:

```
request_id  ->  agent_run_id  ->  step_execution / step_id
```

## Error Handling

* Validation errors → `422` with field details and `request_id`.
* Not found → `404`.
* Unexpected errors → `500` with a **safe** body: `{"error":"Internal server
  error","request_id":"..."}`. Stack traces, API keys, DB passwords, connection
  strings and filesystem paths are never returned to clients (they are logged
  server-side only).

## Configuration

Validated at startup (`src/config.py::validate_config`).

| Variable | Requirement |
| --- | --- |
| `DATABASE_URL` | **Required** — clear startup error if missing |
| `OPENAI_API_KEY` | **Optional / fallback** — absence falls back to Ollama, then offline mode |
| `OPENAI_MODEL`, `OLLAMA_MODEL`, `OLLAMA_BASE_URL`, `ENV` | Optional tuning |

Secret **values** are never printed or logged — only their presence.

## Agent Run & Step Tracking

Runs are persisted to `agent_runs` with lifecycle status (`running` →
`completed` / `failed` / `approval_required`) plus telemetry (step counters,
retries, duration, confidence, tools used). Individual tool executions are
recorded in `step_executions` (tool name, status, duration, retry count, safe
error message). A failed tool is always recorded as `failed` — never silently
reported as success. The live DB handle is stripped before any payload is
stored.

## Database & Migrations

Run migrations (do **not** rely on `create_all` in production):

```bash
alembic upgrade head      # apply
alembic downgrade -1      # roll back one step
alembic current           # show current revision
```

Milestone-4 migrations (safe, reversible, idempotent):

* `b1f2a3c4d5e6` — agent-run execution-summary columns.
* `c2d3e4f5a6b7` — observability indexes on
  `agent_runs(created_at,status,session_id)` and
  `step_executions(agent_run_id,tool_name,status)`.

## Observability API

Read-only, aggregated telemetry (no raw payloads exposed):
`GET /observability/{health,tools,failures,trends,overview}` plus the
management API under `/runs` (list/detail/search/statistics, bounded
pagination `page_size ≤ 100`).

## Running Tests

```bash
pytest                    # full suite (SQLite-backed, no Postgres/OpenAI needed)
```

---

# Deployment, Docker, CI/CD & Operations (Milestone 5)

This milestone makes the application reproducibly deployable without changing
the agent architecture (API → AgentController → Planner → ToolExecutor →
Verifier → Agent Run / Step Audit → PostgreSQL).

## 1. Prerequisites

* Docker Engine 24+ and the Docker Compose plugin (`docker compose`).
* ~4 GB free RAM for the app container (the embedding model is memory-heavy).
* For running *without* Docker: Python 3.13 and a reachable PostgreSQL 15+.
* OpenAI/Ollama are **optional** — the LLM router falls back to offline mode.

## 2. Environment variables

Copy the template and edit it:

```bash
cp .env.example .env
```

| Variable | Type | Purpose |
| --- | --- | --- |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | REQUIRED | PostgreSQL credentials (used by the DB container and to build `DATABASE_URL`). |
| `POSTGRES_PORT` | OPTIONAL | Host port for local DB access (bound to `127.0.0.1`). |
| `DATABASE_URL` | REQUIRED | SQLAlchemy URL. Auto-overridden inside Compose to point at the `postgres` service; set explicitly for host runs. |
| `OPENAI_API_KEY` | FALLBACK | Enables the OpenAI tier. Absent → Ollama → offline fallback. |
| `OPENAI_MODEL` | OPTIONAL | Default `gpt-4o-mini`. |
| `OLLAMA_MODEL` / `OLLAMA_BASE_URL` | FALLBACK | Local inference tier. |
| `DEFAULT_PROVIDER` | OPTIONAL | Preferred tier (`ollama` by default). |
| `ENV` | OPTIONAL | `dev` \| `staging` \| `production`. |
| `CORS_ALLOW_ORIGINS` | OPTIONAL | Comma-separated allow-list, or `*` (default). Credentials auto-enable only for an explicit list. |
| `WEB_CONCURRENCY` | OPTIONAL | uvicorn workers. Keep at `1` (see Production server). |
| `RUN_MIGRATIONS` | OPTIONAL | `1` (default) runs Alembic on startup; `0` skips. |
| `DB_WAIT_TIMEOUT` | OPTIONAL | Seconds to wait for the DB before failing startup. |

**Never** put real secrets in the Dockerfile, `docker-compose.yml`, source,
CI config, or this README — only in `.env` / your platform's secret manager.

## 3. Local development (no Docker)

```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
# set DATABASE_URL in .env to your local Postgres, then:
alembic upgrade head
python -m uvicorn main:app --reload
```

## 4. Docker development / production-like deployment

The full stack (FastAPI + PostgreSQL) runs from `docker-compose.yml`:

```bash
docker compose up --build          # build image + start db + app
docker compose logs -f app         # follow application logs
docker compose ps                  # container + health status
```

On startup the app container's `entrypoint.sh`:

1. waits for PostgreSQL to accept connections (up to `DB_WAIT_TIMEOUT`),
2. runs `python -m alembic upgrade head` (**fails hard** if migrations fail —
   it never serves traffic against an incompatible schema),
3. starts uvicorn (`main:app`) with proxy headers and graceful shutdown.

The API is available at `http://localhost:8000`.

## 5. Database migrations

Alembic is the sole production migration mechanism (do **not** rely on
`create_all`):

```bash
# inside the running app container:
docker compose exec app python -m alembic upgrade head     # apply
docker compose exec app python -m alembic downgrade -1     # roll back one
docker compose exec app python -m alembic current          # current revision
```

Migrations run automatically at container start; set `RUN_MIGRATIONS=0` to
manage them out-of-band (e.g. a dedicated migration job).

## 6. Running tests

The suite is fully self-contained (SQLite, no PostgreSQL/OpenAI needed):

```bash
pytest                # 94 tests
```

## 7. Continuous Integration

`.github/workflows/ci.yml` runs on pushes/PRs to `main`/`master`:

1. **Lint & Test** — compile check (`compileall`) + `pytest` on SQLite.
2. **Migration check** — `alembic upgrade head` → `downgrade base` → re-upgrade
   against a real `pgvector/pgvector:pg15` service (validates reversibility).
3. **Docker build** — builds the production image (GHA layer cache) and smoke
   tests `/health` and `/health/ready` against a Postgres service.

No production secrets are required for CI.

## 8. Health, readiness & Swagger

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Liveness — process is up (used by container HEALTHCHECK). |
| `GET /health/ready` | Readiness — DB reachable + required config present; `503` otherwise. |
| `GET /docs` | Swagger / OpenAPI UI. |

## 9. Smoke test

After the stack is up:

```bash
python scripts/smoke_test.py                       # full: health→ready→docs→stats→list→run→retrieve
python scripts/smoke_test.py --skip-run            # read-only checks (no LLM call)
python scripts/smoke_test.py --base-url http://host:8000
```

## 10. Logs

Logs stream to stdout/stderr (12-factor) — view with `docker compose logs -f app`
or `docker logs <container>`. Structured records carry `request_id`,
`agent_run_id`, `step_id`, `status` and `duration`; secret values and large
payloads are never logged. `PYTHONUNBUFFERED=1` ensures no log buffering.

## 11. Production server configuration

* **Single worker (`WEB_CONCURRENCY=1`).** Each uvicorn worker loads its own
  sentence-transformer embedding model (hundreds of MB). The workload is I/O-
  and inference-bound and largely `async`, so scale **horizontally with
  container replicas**, not with in-container workers.
* uvicorn is launched with `--proxy-headers --forwarded-allow-ips "*"`
  (correct client IP/scheme behind a load balancer), `--timeout-keep-alive 30`
  and `--timeout-graceful-shutdown 30`.

## 12. Graceful shutdown & restart behaviour

* `docker compose restart` / SIGTERM → uvicorn drains in-flight requests within
  the 30 s graceful window; DB sessions are opened per-request and closed in a
  `finally`, so no connection leak on shutdown.
* `restart: unless-stopped` policy auto-recovers crashed containers.
* Qdrant is embedded (on-disk at `/app/qdrant_data`, a named volume) and the HF
  model cache is a named volume, so restarts don't re-download models.

## 13. Data persistence & backup

* PostgreSQL data lives in the `postgres_data` named volume — it **survives**
  `docker compose down` / `up`.
* **Do not** use `docker compose down -v` unless you intend to destroy the
  database (that removes the volume).
* Backup example:

  ```bash
  docker compose exec postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup.sql
  ```

## 14. Security notes

* Container runs as a non-root user (`appuser`, uid 10001).
* `.env` and secrets are excluded from the image (`.dockerignore`) — nothing
  secret is baked into image layers.
* PostgreSQL is **not** exposed publicly: the host port binds to
  `127.0.0.1` only, and the app reaches the DB over the private Compose network.
* Only port `8000` (the API) is published.
* CORS is environment-driven and defaults to safe behaviour (no credentials
  with a wildcard origin).
* No debug mode / `--reload` in the production image.

## 15. Resource limits

Compose sets starting-point limits: app `mem_limit: 4g / cpus: 2.0`,
postgres `1g / 1.0`. Tune these to your host after observing real usage; the
4 GB app limit accommodates the embedding model.

## 16. Troubleshooting

| Symptom | Likely cause / fix |
| --- | --- |
| App exits immediately, logs `Missing required configuration: DATABASE_URL` | Set `DATABASE_URL` (or the `POSTGRES_*` vars for Compose). |
| App exits with `database not reachable after Ns` | Postgres not healthy yet or wrong `DATABASE_URL`; check `docker compose logs postgres`. |
| Startup aborts during "applying database migrations" | A migration failed — fix it; the app intentionally refuses to serve against a bad schema. |
| `/health/ready` returns `503` | DB down or required config missing — inspect the `checks` object. |
| LLM answers are generic / offline | `OPENAI_API_KEY` unset and Ollama unreachable — expected fallback, not an error. |

## 17. Deployment platform recommendations

The image is a standard non-root Python web service and runs on any container
platform. Requirements to provision externally:

* **PostgreSQL 15+ with the `pgvector` extension** (managed DB recommended).
* Persistent disk for the embedded Qdrant store + HF cache, **or** switch to a
  managed Qdrant/remote vector store for multi-replica deployments (the current
  on-disk Qdrant is single-writer — see Remaining risks).

Suitable platforms: **Render**, **Railway**, **Fly.io** (attach a volume),
**AWS ECS/Fargate + RDS**, **Google Cloud Run + Cloud SQL**, **Azure Container
Apps + Azure Database for PostgreSQL**. Set env vars via the platform's secret
manager; run migrations via the entrypoint or a one-off release command.

---

# Authentication & User Isolation (Milestone 6)

Authentication is enforced at the API/security layer — the agent core
(Planner/Executor/Verifier/Controller) is unchanged.

## Endpoints

| Endpoint | Purpose |
| --- | --- |
| `POST /auth/register` | Create an account (`{email, password}`; password ≥ 8 chars). Returns the user **without** the password hash. |
| `POST /auth/login` | OAuth2 password flow (form fields `username`=email, `password`). Returns a JWT bearer token. |
| `GET /auth/me` | The authenticated user's profile. |

Passwords are bcrypt-hashed (never stored or logged in plaintext). Login returns
a single generic error for both unknown-email and wrong-password (no account
enumeration).

## Protected resources

`POST /run`, `POST /run-stream` and every `GET /runs/*` endpoint now require a
bearer token. Each run is associated with the authenticated user (`user_id`).

* **User isolation:** a user only ever sees their own runs across
  `/runs`, `/runs/{id}`, `/runs/search`, `/runs/session/{id}`,
  `/runs/status/{status}` and `/runs/statistics`.
* **No IDOR:** requesting another user's run id returns `404` (existence is
  never leaked), not `403`.
* **Session ids are not authorization:** `/runs/session/{id}` is always scoped
  to the authenticated owner.
* **Admins** (`is_admin` on the DB record — never grantable via the API) see all
  runs and are the only role permitted on the admin-only `/observability/*`
  analytics.

## Swagger

Open `/docs`, click **Authorize**, and log in with the OAuth2 password flow
(email as username). Protected endpoints can then be exercised from Swagger.

## Configuration (see `.env.example`)

| Variable | Notes |
| --- | --- |
| `JWT_SECRET_KEY` | **Required in production** (no default — app refuses to start without it). Insecure dev fallback outside production. |
| `JWT_ALGORITHM` | Default `HS256`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Default `60`. |
| `RATE_LIMIT_ENABLED` | `true` (default) / `false`. |
| `AUTH_RATE_LIMIT` / `RUN_RATE_LIMIT` | slowapi limits for auth and `/run` (defaults `10/minute`, `30/minute`). |

## Migration

`alembic upgrade head` creates the `users` table and adds a **nullable**
`agent_runs.user_id` FK (indexed, `ON DELETE SET NULL`). Existing runs are
preserved as "unowned" (`user_id = NULL`, visible only to admins) — no data is
destroyed and no `NOT NULL` column is added to a populated table.

---

# Final Notes

This project demonstrates:

* Real AI backend engineering
* Local LLM integration
* Semantic AI pipelines
* Modern async Python architecture
* Production-oriented AI infrastructure

It serves as a strong foundation for building advanced AI systems, RAG applications, and autonomous AI workflows.
