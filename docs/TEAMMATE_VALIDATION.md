# MRPL — Teammate Validation Runbook (Ollama + Real OCR)

This runbook lets a teammate **without Claude Code** validate the two things the
dev box cannot: real **Ollama** local inference and real **Tesseract/Poppler**
OCR. Clone/pull the repo, follow the steps, tick the checklist, and record any
failures using the template at the bottom.

The commands are written for **Windows PowerShell** (the primary target). macOS/
Linux equivalents are noted where they differ.

---

## Two supported modes

The application ships with two documented, fully-local modes. **Mode A is the
default and never requires Ollama.** Mode B is what this runbook validates.

| | Mode A — Development / Safe Demo | Mode B — Sovereign AI Validation |
|---|---|---|
| `LLM_PROVIDER` | `mock` | `ollama` |
| `EMBEDDINGS_PROVIDER` | `local` | `local` |
| `OLLAMA_MODEL` | — | `<an installed model>` |
| LLM inference | deterministic offline mock | local Ollama |
| OCR | not exercised (demo PDF is text) | local Tesseract + Poppler |
| Needs OpenAI? | No | No |
| Needs GPU? | No | Recommended for Ollama |

> **Ollama is never mandatory.** If Ollama is unreachable the app stays up; with
> `LLM_PROVIDER=ollama` a failed call fails **closed** (a "not verified" degraded
> result), it does not crash.

### Network honesty

- **Initial setup requires internet** to install Ollama, pull a model, install
  Tesseract/Poppler, and `pip install` / `npm install`.
- **After** everything is installed and models are cached, the accurate claim is:

  > **Runtime inference can operate locally without external AI services.**
  > Ollama is local, Tesseract is local, Poppler is local, embeddings are local,
  > Qdrant is local, document processing is local. No OpenAI, no cloud OCR, no
  > external AI API is contacted at runtime.

---

## PART 1 — Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Python | 3.11+ | `python --version` |
| Node.js | 18+ | `node --version` |
| PostgreSQL | 13+ (or Docker) | `docker --version` |
| Ollama | latest | `ollama --version` |
| Tesseract | 5.x | `tesseract --version` |
| Poppler | latest | `pdftoppm -h` |

Install Python + Node deps first:

```powershell
pip install -r requirements.txt
pip install -r requirements-ocr.txt      # OCR extras: pytesseract, pdf2image, Pillow
cd frontend; npm install; cd ..
```

> `ollama` (the Python package) is intentionally **not** in `requirements.txt`.
> Install it so `LLM_PROVIDER=ollama` can reach the local server:
> ```powershell
> pip install ollama
> ```

---

## PART 2 — Ollama setup

### 2.1 Install & start

- Download from <https://ollama.com/download> and install.
- Ollama usually runs as a background service. If not, start it:

```powershell
ollama serve
```

### 2.2 Pull a model

Pick a **lightweight model that follows JSON-structured instructions** (the
planner and verifier prompts require valid JSON). Choose based on your GPU/RAM:

```powershell
ollama pull llama3.1:8b     # good instruction-following, ~5 GB
# alternatives:
# ollama pull qwen2.5:7b
# ollama pull mistral:7b
# ollama pull phi3:mini     # smallest, weakest JSON adherence
```

Do **not** hardcode a model in the app — you select it via `OLLAMA_MODEL`.

### 2.3 Verify the model exists and inference works

```powershell
ollama list                                   # model should be listed
ollama run llama3.1:8b "Reply with the JSON: {""ok"": true}"
# or hit the local API directly:
curl http://localhost:11434/api/tags
```

---

## PART 3 — OCR setup

### 3.1 Tesseract

- **Windows:** install the UB Mannheim build
  <https://github.com/UB-Mannheim/tesseract/wiki>, then add its folder
  (e.g. `C:\Program Files\Tesseract-OCR`) to **PATH**.
- **macOS:** `brew install tesseract` · **Linux:** `sudo apt-get install tesseract-ocr`

Verify:

```powershell
tesseract --version
```

### 3.2 Poppler (required by `pdf2image` to rasterize PDFs)

- **Windows:** download from
  <https://github.com/oschwartz10612/poppler-windows/releases>, extract, and add
  the `poppler-xx\Library\bin` folder to **PATH**.
- **macOS:** `brew install poppler` · **Linux:** `sudo apt-get install poppler-utils`

Verify (the pipeline calls `pdftoppm` via `pdf2image`, resolved from PATH):

```powershell
pdftoppm -h
pdfinfo -v
```

> Open a **new** terminal after editing PATH so the changes take effect.

---

## PART 4 — Environment (`.env`)

Copy the template and set Mode B. Never commit real secrets — `.env` is
git-ignored.

```powershell
Copy-Item .env.example .env
```

Ensure `.env` contains:

```
LLM_PROVIDER=ollama
EMBEDDINGS_PROVIDER=local
OLLAMA_MODEL=llama3.1:8b
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TEMPERATURE=0.0
LLM_TIMEOUT_SECONDS=120
RAG_SIMILARITY_THRESHOLD=0.3
DATABASE_URL=postgresql+psycopg2://<user>:<pass>@localhost:5432/<db>
```

> A local 7–8B model is slower than the mock. If you see timeouts, raise
> `LLM_TIMEOUT_SECONDS` (e.g. 180).

Run the preflight (never prints secrets):

```powershell
python scripts/check_demo_environment.py
```

It reports Database / Qdrant / LLM provider / embeddings / OCR and prints
`DEMO ENVIRONMENT READY` or `NOT READY`. `OCR ... WARN` is only informational.

---

## PART 5 — Start backend

```powershell
docker compose up -d postgres      # or use your own PostgreSQL
uvicorn main:app --reload          # http://127.0.0.1:8000
```

The backend creates tables and initializes the embedded Qdrant collection on
startup. On startup it logs `LLM tier=ollama model=<your model>` the first time
an analysis runs.

## PART 6 — Start frontend

```powershell
cd frontend
npm run dev                        # http://127.0.0.1:5173
```

---

## PART 7 — Test the TEXT PDF (baseline)

1. Open <http://127.0.0.1:5173>, register / sign in.
2. Go to **MRPL Inspection Intelligence**.
3. Upload `data/demo/mrpl_inspection_report.pdf`.
4. Click **Analyze Inspection Report**.
5. Confirm findings render. Extraction method should be **TEXT**.

This confirms the Ollama path end-to-end on an easy (native-text) document
before adding OCR.

## PART 8 — Test the SCANNED PDF (real OCR)

1. Upload `data/demo/mrpl_scanned_inspection_report.pdf` (5 image-only pages).
2. Click **Analyze Inspection Report**.
3. Confirm extraction method is **OCR** and findings still appear with page
   provenance.

> Regenerate the fixture if needed:
> ```powershell
> python scripts/generate_scanned_fixture.py
> ```

## PART 9 — Verify

For each upload, confirm on screen (and in the downloaded report):

- **Extraction method** — TEXT for Part 7, OCR for Part 8
- **Page count** — 5 for both fixtures
- **Findings** — one or more, evidence-backed
- **Evidence** — quoted text under each finding
- **Page provenance** — each finding cites a `Page N`
- **Verification** — approved / requires-review verdict shown
- **Agent trace** — click **View agent trace**: Planner → RAG Retrieval →
  Inspection Findings → Verifier
- **Report download** — **Download Inspection Report** produces a PDF that
  matches the on-screen analysis

### What "success" means with a REAL model

The local model does **not** have to reproduce the mock provider's exact four
findings. A run is **valid** when:

1. findings are **evidence-grounded** (tied to retrieved document text),
2. **page provenance is valid** (cited pages were actually retrieved),
3. **severity** is one of `LOW / MEDIUM / HIGH / CRITICAL`,
4. **evidence** text is present for each finding,
5. the **verifier accepts** valid findings,
6. **invalid** findings are **rejected** (not shown),
7. **no fabricated pages** are returned (the evidence guard drops them).

Fewer or differently-worded findings from a real model is expected and fine.
What must hold is grounding, valid provenance, valid severity, and verifier
behavior. If the model emits malformed JSON, record it (see the template) — do
not paper over it; that is exactly the signal this validation exists to surface.

## PART 10 — Troubleshooting

| Symptom | Likely cause | Fix |
|--------|--------------|-----|
| `check_demo_environment` LLM shows WARN | `LLM_PROVIDER` not `ollama`/`mock` | set it in `.env`, restart backend |
| Analysis returns a "not verified / degraded" result | Ollama unreachable → fail-closed offline sentinel | start `ollama serve`; check `OLLAMA_BASE_URL`; `ollama list` |
| `model 'x' not found` in logs | model not pulled or name mismatch | `ollama pull <model>`; set `OLLAMA_MODEL` to the exact `ollama list` name |
| Analysis very slow / times out | small GPU / large model | raise `LLM_TIMEOUT_SECONDS`; use a smaller model (`phi3:mini`) |
| Scanned PDF errors with "OCR unavailable" / "Tesseract not found" | Tesseract not on PATH | install Tesseract, add to PATH, open a new terminal |
| Scanned PDF errors mentioning "Poppler" / `pdftoppm` | Poppler not on PATH | install Poppler, add `bin` to PATH, new terminal |
| Upload rejected as too large (413) | body-size limit | raise `UPLOAD_MAX_REQUEST_BYTES` in `.env` |
| Backend won't start: `DATABASE_URL not found` | no `.env` / DB not set | copy `.env.example`; `docker compose up -d postgres` |
| `Qdrant ... store is locked` | embedded Qdrant opened by two processes | stop other backend / CLI script using `./qdrant_data` |
| No findings returned | retrieval threshold too high or weak model | lower `RAG_SIMILARITY_THRESHOLD` (e.g. 0.25); try a stronger model |
| Malformed LLM output / verifier rejects everything | model not following JSON schema | switch to a stronger instruction-following model; keep `OLLAMA_TEMPERATURE=0.0` |

---

## Validation checklist

Copy this and tick as you go.

```
OLLAMA
[ ] Ollama installed
[ ] Ollama running
[ ] Model installed (ollama list shows it)
[ ] Local inference works (ollama run / /api/tags)
[ ] Planner produced a valid plan
[ ] RAG retrieval ran
[ ] Inspection findings produced
[ ] Verifier ran and gave a verdict

OCR
[ ] Tesseract installed (tesseract --version)
[ ] Poppler installed (pdftoppm -h)
[ ] Scanned PDF detected as OCR
[ ] OCR executed
[ ] Page count correct (5)
[ ] Page provenance correct
[ ] OCR text non-empty

FULL DEMO
[ ] Upload works
[ ] Analysis works
[ ] Findings displayed
[ ] Verification displayed
[ ] Agent trace works
[ ] PDF report downloads
[ ] No external AI API required at runtime
```

### Automated OCR check (optional)

With Tesseract + Poppler installed, the skip-gated integration test runs for real:

```powershell
python -m pytest tests/test_ocr_integration.py -v
```

If the binaries are present, `test_real_ocr_pipeline_on_scanned_fixture` runs
(instead of skipping) and asserts OCR selection, page count, non-empty text and
per-page provenance.

---

## Failure report template

For every failed item, record:

```
FAIL:   <what happened>
ERROR:  <exact error / log line>
MODEL:  <ollama model name, e.g. llama3.1:8b>
OS:     <e.g. Windows 11 / macOS 14 / Ubuntu 22.04>
STEP:   <which PART / checklist item>
```
