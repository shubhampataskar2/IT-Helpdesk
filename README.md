# AI-Powered IT Helpdesk

A full-stack enterprise IT helpdesk where employees file tickets and an AI assistant
triage, summarizes, deduplicates, suggests fixes, and surfaces KB articles via semantic
search — while a clean RBAC + SLA + analytics backend keeps the operation auditable.

## Stack

- **Backend:** FastAPI, SQLAlchemy 2.0, PostgreSQL 14+ with **pgvector**, Alembic, Celery (Redis), JWT auth, slowapi rate limiting, pytest.
- **AI:** pluggable providers (`OpenAIProvider` via `AI_PROVIDER=openai`, `HeuristicProvider` keyword scoring fallback with no API key).
- **RAG:** pgvector cosine search over embedded KB articles (keyword `ILIKE` fallback when no embeddings exist).
- **Frontend:** Next.js 15 (App Router), React 19, Tailwind, Recharts — dashboard, ticket workflows, KB search, admin console.

## Features

- **Auth & RBAC** — register/login, rotating refresh tokens, roles `employee` / `support` / `admin` enforced server-side.
- **Tickets** — create, filter/search, comments, SLA deadlines, assignment, guarded status transitions (`TICKET_TRANSITIONS`), reopen (owner), force-close (admin), duplicate detection.
- **AI assistance** — category + priority + summary + suggested fix + confidence from the create flow, refined asynchronously (background thread or Celery task) and persisted to the ticket.
- **Knowledge base** — CRUD (admin), similarity search ranked by score.
- **Observability** — audit log, SLA compliance per priority, engineer performance, trend charts.
- **Email** — SMTP notifications on create/assign/resolve via `send_mail`; gracefully falls back to console when SMTP is not configured.

## Quick start (Docker)

```bash
cp .env.example .env        # set OPENAI_API_KEY to use GPT typing; heuristic fallback otherwise
docker compose up --build
```

- Frontend: http://localhost:3000
- API docs:  http://localhost:8000/docs
- Seed admin: `admin@helpdesk.io` / `admin123!`

### Run without Docker (backend)

```bash
# Postgres with pgvector available, then:
pip install -r backend/requirements.txt
cd backend
alembic upgrade head
uvicorn app.main:app --reload
```

## Tests

```bash
cd backend
python3 -m pytest app/tests -q
```

Requires Postgres once (tests use a `helpdesk_test` database).

## CI

`.github/workflows/ci.yml` runs ruff + pytest (pgvector service) + Next.js build + `docker compose build`.

## Environment (`.env.example`)

| Variable | Default | Purpose |
|---|---|---|
| `AI_PROVIDER` | `heuristic` | `openai` or `heuristic` |
| `OPENAI_API_KEY` | | used when provider is `openai` |
| `DATABASE_URL` | | SQLAlchemy DSN |
| `JWT_SECRET` | | signing key |
| `REDIS_URL` / `RATE_LIMIT_STORAGE` | | Celery broker + slowapi backend |
| `USE_CELERY` | `true` | `true` → Celery tasks, `false` → inline background threads |
| `MAIL_*` | | optional SMTP |
| `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` | `admin@helpdesk.io` / `admin123!` | bootstrap user |

## Project layout

```
backend/app/
  api/v1/        auth, users, tickets, kb, analytics, admin routers
  core/          config, security, database, jobs, rate_limit, constants
  ai/            provider base, factory, heuristic, openai
  rag/           semantic + keyword KB search, duplicate detection
  models/        SQLAlchemy models
  schemas/       Pydantic schemas
  services/      auth, ticket, kb, email, sla, analytics, audit, bootstrap
  workers/       celery app + tasks
  tests/         pytest suite (29 tests)
frontend/
  app/           Next.js pages (dashboard, tickets, KB, admin)
  components/    auth, layout, UI primitives
  lib/           typed API client + shared types
```

## API surface

```
POST /api/v1/auth/register|login|refresh        GET  /api/v1/auth/me
POST /api/v1/tickets                            GET/PATCH /api/v1/tickets/{id}
POST /api/v1/tickets/{id}/assign|resolve|reopen POST /api/v1/tickets/{id}/comments
GET  /api/v1/tickets?status=&priority=&category=&q=&mine=
GET/POST /api/v1/kb      GET /api/v1/kb/search  DELETE /api/v1/kb/{id}
GET  /api/v1/analytics/overview|sla|engineers
GET  /api/v1/users       PATCH /api/v1/users/{id}/role|active
GET  /api/v1/admin/audit-logs
```