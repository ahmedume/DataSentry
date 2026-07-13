# For the Dev — Running, Maintaining & Debugging DataSentry

## First-Time Setup

```bash
# 1. Clone and enter
cd datasentry

# 2. Backend
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env

# 3. Edit .env — at minimum set:
#    JWT_SECRET=<random-32-char-string>
#    GOOGLE_API_KEY=<your-gemini-key>  (optional, heuristics work without it)

# 4. Start backend
.venv\Scripts\uvicorn app.main:app --reload --port 8000

# 5. Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

---

## Starting / Stopping Everything

### Backend (FastAPI)
```bash
cd backend

# Start (dev mode, auto-reload)
.venv\Scripts\uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Or start and log to file (background)
start /B .venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 > backend.log 2>&1

# Stop — Ctrl+C in the terminal, or if background:
taskkill /F /IM uvicorn.exe

# Verify it's running
curl http://localhost:8000/health
# → {"status":"ok"}
```

### Frontend (Next.js)
```bash
cd frontend

# Start (dev mode)
npm run dev

# Production build + start
npm run build && npm start

# Stop — Ctrl+C, or if background:
taskkill /F /IM node.exe
```

### Quick-launch batch scripts (in project root)
```bash
run_backend.bat    # launches backend, logs to backend/backend.log
run_frontend.bat   # launches frontend, logs to frontend/frontend.log
```

### Docker Compose (full stack)
```bash
cd datasentry
docker compose up --build

# Services:
#   postgres:5432 — PostgreSQL database
#   redis:6379 — Celery broker
#   backend:8000 — FastAPI
#   celery — background task worker
#   beat — scheduled task scheduler
#   frontend:3000 — Next.js

# Stop
docker compose down

# Wipe volumes (reset postgres data)
docker compose down -v
```

---

## URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Health check | http://localhost:8000/health |

---

## Frontend Routes

| Route | What it does |
|-------|-------------|
| `/` | Cinematic landing page + CSV upload dropzone |
| `/login` | JWT login |
| `/register` | Create account |
| `/connectors` | Manage local/Postgres/S3 data sources |
| `/monitor` | Drift monitoring schedules + run history |
| `/training` | Start training jobs, inspect metrics |
| `/teams` | Create teams, invite members, change roles |
| `/webhooks` | Create webhooks (select events), toggle on/off, delete |
| `/models` | Model registry — filter by stage, promote, view metrics/importances |
| `/audit` | Immutable audit log (paginated, limit selector) |
| `/usage` | API usage metering table with totals |
| `/datasets/[id]` | Dataset detail — 7 tabs: Overview, Quality, Insights, Cleaning, Charts, Report, Annotations |

---

## Database

### Dev (SQLite — default)
- File: `backend/datasentry.db` (auto-created on first startup)
- Tables are auto-created on startup (`init_db()`)
- Reset: delete the file and restart the backend
- Not suitable for multi-user or production

```bash
# Browse with sqlite3 CLI
sqlite3 backend\datasentry.db

# Useful commands inside sqlite3:
.tables
.schema datasets
SELECT * FROM datasets;
SELECT * FROM users;
SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 10;
.quit

# GUI alternative: DB Browser for SQLite (free, sqlitebrowser.org)
# Just open backend\datasentry.db directly
```

### Production (PostgreSQL)
Set in `.env`:
```
DATABASE_URL=postgresql://datasentry:datasentry@localhost:5432/datasentry
```

Migrations use Alembic:
```bash
# Run pending migrations
.venv\Scripts\python -m alembic upgrade head

# Create a new migration after model changes
.venv\Scripts\python -m alembic revision --autogenerate -m "description"

# Rollback one step
.venv\Scripts\python -m alembic downgrade -1

# View history
.venv\Scripts\python -m alembic history

# Check current revision
.venv\Scripts\python -m alembic current
```

```bash
# Direct access (when running via docker compose)
docker exec -it datasentry-postgres-1 psql -U datasentry -d datasentry
\dt
SELECT * FROM datasets;
```

### DB Admin GUIs
- **SQLite**: DB Browser for SQLite — open `backend\datasentry.db`
- **PostgreSQL**: pgAdmin, DBeaver, or DataGrip — connect to `localhost:5432`, user `datasentry`, password `datasentry`, database `datasentry`
- There is **no built-in web admin UI** (no Django Admin equivalent). Use the Swagger UI (`/docs`) to explore and test all API endpoints interactively.

---

## Celery (Background Tasks)

```bash
# Dev mode (default): CELERY_EAGER=true in .env
#   → Tasks run synchronously when called. No Redis needed.
#   → Profile, insights, cleaning, report, ingest, train all work inline.

# Production mode: CELERY_EAGER=false
# Terminal 1 — Redis server
redis-server

# Terminal 2 — Celery worker
cd backend && .venv\Scripts\celery -A app.workers.celery_app.celery_app worker --loglevel=info

# Terminal 3 — Celery Beat (scheduled monitors)
.venv\Scripts\celery -A app.workers.celery_app.celery_app beat --loglevel=info
```

The beat schedule runs `run_due_monitors` every 60 seconds, which checks all enabled `MonitorSchedule` entries and fires `run_monitor` for any past their cadence.

---

## Daily Commands

```bash
# Run all tests (40 tests, ~9s)
cd backend && .venv\Scripts\python -m pytest -q --timeout=30 tests/

# Run a specific test file
.venv\Scripts\python -m pytest tests/test_v2.py -q --timeout=30

# Run a single test
.venv\Scripts\python -m pytest tests/test_v2.py::test_drift_same_data_is_stable -q

# Run with coverage
.venv\Scripts\python -m pytest --cov=app tests/

# Auto-format code
.venv\Scripts\python -m black app/ tests/
.venv\Scripts\python -m ruff check app/ tests/

# Build frontend (checks for type errors)
cd frontend && npm run build

# Lint frontend
cd frontend && npm run lint
```

---

## API Key Usage (Programmatic Access)

```bash
# Create a key (requires JWT first)
curl -X POST http://localhost:8000/api/v1/auth/api-keys \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"name":"ci","scopes":["datasets:read","datasets:write"]}'

# Use the key
curl http://localhost:8000/api/v1/public/datasets/<id> \
  -H "X-API-Key: dsk_<key_id>_<secret>"

# Available scopes: datasets:read, datasets:write, drift:read, models:read, *
```

---

## Piping Data Through the Platform

```bash
# 1. Upload a CSV
curl -X POST http://localhost:8000/api/v1/datasets/upload \
  -F "file=@data.csv"

# 2. Check profile status
curl http://localhost:8000/api/v1/datasets/<id>/profile

# 3. Get AI insights
curl http://localhost:8000/api/v1/datasets/<id>/insights

# 4. List cleaning recommendations
curl http://localhost:8000/api/v1/datasets/<id>/recommendations

# 5. Apply cleaning
curl -X POST http://localhost:8000/api/v1/datasets/<id>/cleaning/apply \
  -H "Content-Type: application/json" \
  -d '{"accepted_recommendation_ids":["<rec-id>"]}'

# 6. Download cleaned CSV
curl http://localhost:8000/api/v1/datasets/<id>/download/cleaned -o cleaned.csv

# 7. Generate PDF report
curl -X POST http://localhost:8000/api/v1/datasets/<id>/report
curl http://localhost:8000/api/v1/datasets/<id>/report/download -o report.pdf
```

---

## Webhooks

Events available: `dataset.uploaded`, `dataset.profiled`, `cleaning.completed`, `drift.alert`, `training.completed`, `monitor.run`

```bash
# Create
curl -X POST http://localhost:8000/api/v1/webhooks \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://hooks.example.com/datasentry","events":["dataset.uploaded","drift.alert"]}'

# Toggle active/inactive
curl -X POST http://localhost:8000/api/v1/webhooks/<id>/toggle \
  -H "Authorization: Bearer <jwt>"

# Delete
curl -X DELETE http://localhost:8000/api/v1/webhooks/<id> \
  -H "Authorization: Bearer <jwt>"
```

Payloads are signed with `X-DataSentry-Signature: HMAC-SHA256(secret, body)`.

---

## Monitoring Schedules

```bash
# Create a monitor
curl -X POST http://localhost:8000/api/v1/monitors \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"name":"daily","source_type":"dataset","source_id":"<id>","cadence_minutes":1440}'

# Run immediately
curl -X POST http://localhost:8000/api/v1/monitors/<id>/run \
  -H "Authorization: Bearer <jwt>"

# View runs
curl http://localhost:8000/api/v1/monitors/<id>/runs \
  -H "Authorization: Bearer <jwt>"
```

---

## Teams

```bash
# Create a team
curl -X POST http://localhost:8000/api/v1/teams \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"name":"data-science"}'

# List your teams
curl http://localhost:8000/api/v1/teams \
  -H "Authorization: Bearer <jwt>"

# Add a member (admin+)
curl -X POST http://localhost:8000/api/v1/teams/<id>/members \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"email":"colleague@company.com","role":"member"}'

# Roles: viewer → member → admin → owner
# Update a member's role (admin+)
curl -X PUT http://localhost:8000/api/v1/teams/<id>/members/<user-id> \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"role":"admin"}'

# Remove a member (admin+)
curl -X DELETE http://localhost:8000/api/v1/teams/<id>/members/<user-id> \
  -H "Authorization: Bearer <jwt>"

# Leave a team (non-owner)
curl -X POST http://localhost:8000/api/v1/teams/<id>/leave \
  -H "Authorization: Bearer <jwt>"

# Delete a team (owner only)
curl -X DELETE http://localhost:8000/api/v1/teams/<id> \
  -H "Authorization: Bearer <jwt>"
```

---

## Model Registry

```bash
# View all models (with registry stage info)
curl http://localhost:8000/api/v1/models/registry \
  -H "Authorization: Bearer <jwt>"

# Promote a model
curl -X POST http://localhost:8000/api/v1/models/<job-id>/promote \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"stage":"staging"}'

# Stages: dev → staging → production

# Predict using a production model
curl -X POST http://localhost:8000/api/v1/models/<job-id>/predict \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"instances":[{"feature1":0.5,"feature2":10}]}'
```

---

## Adding a New Feature

1. **Model** → `app/db/models/` — SQLAlchemy table class
2. **Schema** → `app/schemas/` — Pydantic request/response models
3. **Route** → `app/api/v1/` — FastAPI router with `Depends` auth
4. **Service** → `app/services/` — Business logic
5. **Wire** → `app/main.py` — import router, add to `app.include_router`
6. **Migration** → `alembic revision --autogenerate -m "desc"` then `alembic upgrade head`
7. **Test** → `tests/` — pytest unit + integration tests
8. **Export** → `app/db/models/__init__.py` — add to `__all__`
9. **Frontend type** → `frontend/lib/types.ts` — TypeScript interface
10. **Frontend API** → `frontend/lib/api.ts` — fetch wrapper
11. **Frontend page** → `frontend/app/<name>/page.tsx` — Next.js page
12. **Frontend nav** → `frontend/components/Nav.tsx` — add link

---

## Production Checklist

- [ ] Set `JWT_SECRET` to a cryptographically random 32+ character string
- [ ] Set `ENV=production` (disables auto-migration on startup)
- [ ] Switch from SQLite to PostgreSQL (`DATABASE_URL=postgresql://...`)
- [ ] Set `CELERY_EAGER=false` and run Redis + Celery workers
- [ ] Configure `SMTP_*` for email alerts
- [ ] Set `CORS_ORIGINS` to your frontend domain
- [ ] Set `ALLOW_SIGNUP=false` after creating initial admin users
- [ ] Run `alembic upgrade head` as part of deployment
- [ ] Set `GOOGLE_API_KEY` for LLM-powered insights

---

## Debugging

```bash
# Check API logs
type backend\backend.log

# Health check
curl -v http://localhost:8000/health

# View DB tables (SQLite)
sqlite3 backend\datasentry.db ".tables"

# Check migration status
.venv\Scripts\python -m alembic current
.venv\Scripts\python -m alembic history

# Test auth
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <token>"

# Test API key auth
curl http://localhost:8000/api/v1/public/datasets/ \
  -H "X-API-Key: dsk_<key_id>_<secret>"

# View recent audit log
curl http://localhost:8000/api/v1/audit?limit=10 \
  -H "Authorization: Bearer <token>"

# View usage metering
curl http://localhost:8000/api/v1/usage \
  -H "Authorization: Bearer <token>"

# Run frontend type check
cd frontend && npx tsc --noEmit
```

---

## File Layout (Key Paths)

```
datasentry/
├── backend/
│   ├── .env                  # Local config (git-ignored)
│   ├── .env.example          # Template (committed)
│   ├── app/
│   │   ├── main.py           # FastAPI app + lifespan + router wiring
│   │   ├── api/v1/           # 20 routers
│   │   ├── core/             # config, security, deps, rbac, audit, storage, middleware, ids
│   │   ├── db/
│   │   │   ├── session.py    # Engine + SessionLocal + Base + init_db()
│   │   │   └── models/       # 19 SQLAlchemy models
│   │   ├── schemas/          # Pydantic request/response models
│   │   ├── services/         # Business logic (14 files)
│   │   └── workers/          # Celery app + tasks
│   ├── migrations/           # Alembic
│   ├── tests/                # 40 tests (8 files)
│   └── requirements.txt
├── frontend/
│   ├── app/                  # 12 Next.js route groups
│   ├── components/           # React components (20+ files)
│   ├── lib/                  # API client (api.ts), auth helpers, types
│   └── package.json
├── docker-compose.yml        # Full-stack orchestration (6 services)
├── .gitignore
├── run_backend.bat           # Quick-launch backend
└── run_frontend.bat          # Quick-launch frontend
```

---

## Key Design Decisions

- **No bcrypt** — password hashing uses stdlib `hashlib.scrypt` to avoid dependencies
- **No PyJWT** — JWT is hand-implemented with stdlib `hmac` + `hashlib.sha256`
- **No scipy** — drift detection (PSI, KS, TVD) is pure numpy/pandas
- **String booleans** — `enabled`, `active`, `delivered` columns use `"true"`/`"false"` (SQLite compat)
- **Inline imports** avoided — all modules use top-level imports
- **`__import__()` eliminated** — all dynamic imports replaced with proper module-level imports
