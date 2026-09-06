# MRPL Inspection Intelligence — SIH Demo Runbook

This is the reproducible procedure to run the **offline** MRPL inspection demo:
document upload → extraction/OCR → RAG → real agent pipeline
(Planner → Executor → Verifier) → evidence-backed findings → downloadable report.

The demo runs **fully local**: `LLM_PROVIDER=mock`, local embeddings, embedded
Qdrant. It needs **no OpenAI, no Ollama, no internet and no GPU**.

> Ollama (`LLM_PROVIDER=ollama`) is validated on a separate GPU-capable machine.
> Do **not** run Ollama for this demo.

---

## 1. Prerequisites

- Python 3.11+ with `pip install -r requirements.txt`
- A PostgreSQL database (the app requires `DATABASE_URL`). The simplest option is
  the bundled Docker Postgres service.
- Node 18+ for the frontend (`cd frontend && npm install`)

Qdrant is **embedded** (a local `./qdrant_data` folder) — nothing to install.

OCR (Tesseract) is **optional**; the demo PDF is text-based, so OCR is not
required on this machine.

---

## 2. Demo configuration

Copy the template and keep the offline defaults:

```bash
cp .env.example .env
```

Ensure `.env` contains (these are already the template defaults):

```
LLM_PROVIDER=mock
EMBEDDINGS_PROVIDER=local
RAG_SIMILARITY_THRESHOLD=0.3
DATABASE_URL=postgresql+psycopg2://<user>:<pass>@localhost:5432/<db>
```

Never commit real secrets. `.env` is git-ignored.

---

## 3. Check the environment

Run the preflight — it verifies dependencies, the database, Qdrant, and the
provider configuration, and prints a single verdict. It never prints secrets.

```bash
python scripts/check_demo_environment.py
```

Expected tail:

```
  [OK  ] Required Python dependencies  all 8 present
  [OK  ] Database                      connected (postgresql)
  [OK  ] Qdrant (embedded)             reachable
  [OK  ] LLM provider                  mock (offline)
  [OK  ] Embedding provider            local
  [WARN] OCR (Tesseract)               unavailable - not required ...
========================================
DEMO ENVIRONMENT READY
```

`OCR ... WARN` is expected and non-blocking. Fix any `FAIL` before continuing
(the line tells you how).

> The embedded Qdrant store is single-process. If the backend is already
> running, the check reports the store as "in use by a running backend" — that
> is fine.

---

## 4. Start the services

### Option A — Docker (database only) + local backend/frontend (recommended)

```bash
# 1) database
docker compose up -d postgres

# 2) backend  (http://127.0.0.1:8000)
uvicorn main:app --reload

# 3) frontend (http://127.0.0.1:5173)
cd frontend && npm run dev
```

### Option B — full Docker stack

```bash
docker compose up --build
# frontend: http://localhost:5173   backend: http://localhost:8000
```

The backend creates its tables on startup; Qdrant initializes automatically.

---

## 5. Run the demo in the browser

1. Open the frontend (`http://127.0.0.1:5173`).
2. Register / sign in (the inspection API requires a valid access token).
3. Go to **MRPL Inspection Intelligence**.
4. Upload `data/demo/mrpl_inspection_report.pdf`.
5. Click **Analyze Inspection Report**.
6. Review the real findings, page provenance and verification verdict.
7. Click **View agent trace** to see the real Planner / RAG / Findings / Verifier steps.
8. Click **Download Inspection Report** to download the PDF report.
9. Click **New Analysis** to reset the page for another run.

All findings come from the backend (`POST /inspection/analyze`) — nothing on the
page is fabricated. **Download Inspection Report** re-formats the analysis you
already see (`POST /inspection/report`); it never re-runs analysis or
re-uploads the document, so it creates no duplicate records.

---

## 6. Headless smoke (no browser)

Run the exact same pipeline from the CLI (regenerate the demo PDF first if
missing):

```bash
python scripts/generate_demo_report.py      # writes data/demo/mrpl_inspection_report.pdf
python scripts/run_inspection_demo.py        # runs the real pipeline, prints the analysis
```

> Stop the dev backend before running `run_inspection_demo.py` — it opens the
> single-process embedded Qdrant store directly.

---

## 7. Expected findings (synthetic demo document)

The demo PDF is **synthetic** (no confidential data). It typically surfaces:

| Page | Finding                | Severity |
|------|------------------------|----------|
| 2    | Equipment wear         | MEDIUM   |
| 3    | Pipe / joint issue     | HIGH     |
| 4    | Corrosion              | HIGH     |
| 5    | Safety hazard          | HIGH     |

Exact wording is produced by the pipeline, not hardcoded in the UI.
