# Backup & Recovery (PostgreSQL)

This document defines the backup, restore, and recovery procedures for the
**AI Process Bottleneck** database. PostgreSQL is the single source of truth for
users, agent runs, execution steps, tasks, approvals and audit logs. The
embedded Qdrant vector store and the Hugging Face model cache are **derived
data** (re-buildable from documents / re-downloadable) and are not part of the
critical backup set.

> ⚠️ A local Docker `postgres_data` volume is **not** a backup strategy. It is a
> single copy on one host with no point-in-time recovery. The procedures below
> are what a real deployment requires.

---

## 1. What to back up

| Data | Criticality | Strategy |
|------|-------------|----------|
| PostgreSQL database | **Critical** | Logical dumps + (prod) PITR / managed snapshots |
| Alembic migration history (`alembic_version`) | Critical | Included in the DB dump |
| Qdrant vector store (`qdrant_data/`) | Derived | Re-ingest from source documents; optional volume snapshot |
| HF model cache (`.cache/`) | Derived | Re-downloaded on first run |
| `.env` / secrets | **Critical, separate** | Store in a secret manager, **never** in the DB backup |

---

## 2. Backup strategy

### Local / single-host (Docker Compose)

Nightly logical dump of the `postgres` service:

```bash
# Compressed custom-format dump (best for selective restore)
docker exec ai_postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -F c \
  > backups/db_$(date +%F).dump
```

Retain at least 7 daily + 4 weekly dumps, stored **off the host** (object
storage). Verify each dump is restorable at least monthly (see §4).

### Production

Use a managed PostgreSQL (RDS / Cloud SQL / Azure Database) with:

- **Automated daily snapshots** + **Point-In-Time Recovery (PITR)** via WAL
  archiving (target RPO ≤ 5 min).
- Snapshots replicated to a second region.
- Scheduled logical `pg_dump` (weekly) as a portable, engine-independent copy.
- Backups **encrypted at rest**; access restricted via IAM.

Targets: **RPO ≤ 5 minutes**, **RTO ≤ 1 hour**.

---

## 3. Restore procedure

```bash
# 1. Provision a fresh, EMPTY database (do not restore over a live DB).
createdb -U "$POSTGRES_USER" "$POSTGRES_DB"

# 2. Restore the custom-format dump.
pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists \
  backups/db_YYYY-MM-DD.dump

# 3. Confirm the schema version matches the app's expected head.
DATABASE_URL=... python -m alembic current   # should equal `alembic heads`

# 4. If the backup predates the current code, apply pending migrations.
DATABASE_URL=... python -m alembic upgrade head

# 5. Start the app and verify readiness.
curl -fsS http://localhost:8000/health/ready
```

For PITR (production): restore the latest snapshot, then replay WAL to the
desired timestamp using the managed provider's console/CLI.

---

## 4. Backup verification (do NOT skip)

A backup is only real once a restore has been proven:

1. Monthly, restore the newest dump into a throwaway database.
2. Run `alembic current` and confirm it equals `alembic heads`.
3. Run the smoke test (`scripts/smoke_test.py`) or hit `/health/ready`.
4. Record the result. A failed verification is a Sev-2 incident.

---

## 5. Migration recovery

- Migrations run automatically on container start (`entrypoint.sh` →
  `alembic upgrade head`) and **fail hard** on error, so the app never serves
  traffic against an incompatible schema.
- The forward path (`alembic upgrade head`) is validated from a fresh database
  in CI against a real PostgreSQL service.
- If a migration fails mid-deploy: the container exits non-zero and does not
  serve. Fix forward (a new corrective migration) rather than editing an
  already-applied revision. Restore from backup only if data was mutated.
- **Known limitation:** `alembic downgrade base` has a SQLite-only issue
  (dropping a foreign-key column); it works on PostgreSQL. Downgrades are a
  recovery tool of last resort — prefer restore-from-backup for data safety.

---

## 6. Database failure behavior (application)

- On DB unavailability the app's `/health/ready` returns **503** (readiness),
  while `/health` (liveness) stays 200 — orchestrators stop routing traffic but
  do not kill the pod.
- A server-side `statement_timeout` (default 30s) prevents a stuck query from
  holding a pooled connection indefinitely.
- Connection-pool exhaustion fails fast (`pool_timeout`, default 30s) instead of
  hanging requests.
