# DataSentry — Dataset Intelligence Platform

**AI-powered data quality monitoring, profiling, cleaning, drift detection, and dataset management.**

DataSentry turns raw CSV uploads into a living, inspectable schema. It profiles every column, surfaces quality issues (missing values, outliers, duplicates, type mismatches), generates AI-powered insights and cleaning recommendations, detects drift over time, and produces PDF reports — all without your data leaving your machine.

---

## Features

| Capability | Description |
|---|---|
| **Instant Profiling** | Column-level statistics: type inference, null rates, distributions, cardinality, skew, outliers — generated the moment a file lands |
| **Quality Audit** | 12 automated quality checks: missing values, duplicates, type mismatches, outliers (IQR), high cardinality, correlation warnings |
| **AI-Powered Insights** | LLM-backed column explanations (Gemini or Groq) with heuristic fallback — explains what each column means and flags risks |
| **Cleaning Engine** | Automated cleaning recommendations (impute, drop, cap, coerce) → user selects → one-click apply → cleaned CSV download |
| **Interactive Charts** | Histograms (numeric), bar charts (categorical), missingness overview — built with Chart.js |
| **PDF Reports** | Full printable report with overview, EDA charts, quality table, AI-generated insights, cleaning diff |
| **Drift Detection** | Snapshot-based drift monitoring: PSI (numeric), KS (numeric), TVD (categorical) — pure numpy/pandas |
| **Model Training** | sklearn RandomForest pipeline → model artifact (.pkl) → registry → promote (dev/staging/production) → predict |
| **Monitoring Schedules** | Celery Beat recurring drift checks + Slack/email alerts + webhooks |
| **Teams & RBAC** | Multi-tenant: owner/admin/member/viewer roles, per-team access control |
| **Connectors** | Local filesystem, PostgreSQL, S3-compatible storage — as data sources |
| **Webhooks** | Outbound event webhooks with HMAC-SHA256 signed payloads |
| **Audit Logging** | Immutable audit trail for all operations |
| **API Key Auth** | Programmatic access with scoped API keys (SHA-256 hashed) |

---

## Architecture Overview

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  Next.js 14 │────▶│  FastAPI     │────▶│  SQLAlchemy  │
│  Frontend   │     │  Backend     │     │  + SQLite/   │
│  :3000      │     │  :8000       │     │  PostgreSQL  │
└─────────────┘     └──────┬───────┘     └──────────────┘
                           │
                    ┌──────┴───────┐
                    │  Celery      │
                    │  (async)     │
                    └──────┬───────┘
                           │
                    ┌──────┴───────┐
                    │  Redis       │
                    │  (broker)    │
                    └──────────────┘
```

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Framer Motion, Chart.js, Three.js |
| **Backend** | FastAPI, SQLAlchemy 2.0 (ORM), Pydantic v2 (validation), Alembic (migrations) |
| **Workers** | Celery (async tasks), Celery Beat (scheduled drift monitoring), Redis (broker) |
| **Database** | PostgreSQL 16 (production) / SQLite (development) |
| **Auth** | JWT (HMAC-SHA256, stdlib-only) + API keys (SHA-256 hashed) + Team RBAC |
| **Storage** | Local filesystem (`.data/`) — swappable to S3/MinIO adapter |
| **LLM** | Google Gemini API + Groq fallback (heuristic fallback when no API key) |

---

## Quick Start (Local Development)

### Prerequisites

- Python 3.14+
- Node.js 18+
- npm 9+

### Backend Setup

```bash
cd datasentry/backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env — at minimum set JWT_SECRET to a random string
# Optionally set GOOGLE_API_KEY or GROQ_API_KEY for LLM features

# Start the API server
.venv\Scripts\uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend Setup

```bash
cd datasentry/frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

### Verify

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Health Check | http://localhost:8000/health |

---

## Project Structure

```
datasentry/
│
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app, lifespan, CORS, router wiring
│   │   │
│   │   ├── api/v1/                    # 20 REST routers
│   │   │   ├── alerts.py              # Rule-based alerting CRUD + evaluation
│   │   │   ├── annotations.py         # Dataset/column annotations
│   │   │   ├── audit.py               # Immutable audit log queries
│   │   │   ├── auth.py                # Register, login, API key management
│   │   │   ├── charts.py              # Histogram, bar chart, missingness endpoints
│   │   │   ├── cleaning.py            # Recommendations + apply transforms + diff
│   │   │   ├── connectors.py          # Data source connectors CRUD
│   │   │   ├── datasets.py            # Upload, list, get, status
│   │   │   ├── drift.py               # Snapshots, PSI/KS/TVD comparison
│   │   │   ├── insights.py            # AI column insights (trigger + get)
│   │   │   ├── models_v4.py           # Model registry, promote, predict
│   │   │   ├── monitoring.py          # Monitor schedules + runs
│   │   │   ├── profiling.py           # Column profiling results
│   │   │   ├── public.py              # API-key-authenticated public endpoints
│   │   │   ├── reports.py             # PDF report generation + download
│   │   │   ├── teams.py               # Team CRUD + member management
│   │   │   ├── training.py            # ML training pipeline
│   │   │   ├── usage.py               # API usage metering
│   │   │   └── webhooks.py            # Outbound webhooks CRUD + toggle
│   │   │
│   │   ├── core/
│   │   │   ├── config.py              # Pydantic Settings (env-driven config)
│   │   │   ├── security.py            # Password hashing (scrypt), JWT, API keys
│   │   │   ├── deps.py                # FastAPI dependencies (auth, access control)
│   │   │   ├── rbac.py                # Team role-based access (viewer→owner)
│   │   │   ├── audit.py               # record_audit() helper
│   │   │   ├── middleware.py          # UsageMiddleware (per-endpoint daily counters)
│   │   │   ├── storage.py             # Local filesystem adapter (swappable to S3)
│   │   │   └── ids.py                 # UUID parsing utilities
│   │   │
│   │   ├── db/
│   │   │   ├── session.py             # SQLAlchemy engine, SessionLocal, Base, init_db()
│   │   │   └── models/                # 19 SQLAlchemy ORM models
│   │   │       ├── user.py            # Users + teams relationship
│   │   │       ├── dataset.py         # Dataset records
│   │   │       ├── profiling_result.py
│   │   │       ├── ai_insight.py
│   │   │       ├── cleaning_recommendation.py
│   │   │       ├── cleaned_dataset.py
│   │   │       ├── report.py
│   │   │       ├── api_key.py
│   │   │       ├── connector.py
│   │   │       ├── drift.py           # Drift snapshots
│   │   │       ├── monitoring.py      # Monitor schedules + runs
│   │   │       ├── training.py        # Training jobs
│   │   │       ├── alerts.py          # Alert rules + events
│   │   │       ├── v34.py             # Teams, annotations, webhooks, model registry, audit, usage
│   │   │       └── __init__.py
│   │   │
│   │   ├── schemas/                   # Pydantic v2 request/response models
│   │   │   ├── auth.py
│   │   │   ├── dataset.py
│   │   │   ├── profiling.py
│   │   │   ├── insights.py
│   │   │   ├── cleaning.py
│   │   │   ├── charts.py
│   │   │   ├── reports.py
│   │   │   ├── connectors.py
│   │   │   ├── drift.py
│   │   │   ├── training.py
│   │   │   ├── monitoring.py
│   │   │   ├── alerts.py
│   │   │   ├── v34.py
│   │   │   ├── common.py
│   │   │   └── __init__.py
│   │   │
│   │   ├── services/                  # Business logic (14 modules)
│   │   │   ├── profiler.py            # Pandas column profiling pipeline
│   │   │   ├── quality_checks.py      # Missing%, outliers (IQR), duplicates, cardinality
│   │   │   ├── chart_aggregator.py    # Histogram binning, bar charts, missingness
│   │   │   ├── ai_analyst.py          # LLM + heuristic column explanation generator
│   │   │   ├── ai_cleaner.py          # LLM + heuristic cleaning recommendation engine
│   │   │   ├── cleaning_engine.py     # Transform application (impute, drop, cap, coerce)
│   │   │   ├── report_builder.py      # PDF generation (reportlab + matplotlib)
│   │   │   ├── connectors.py          # SourceConnector abstraction (local, postgres, s3)
│   │   │   ├── drift.py               # PSI, KS, TVD drift metrics (pure numpy/pandas)
│   │   │   ├── training.py            # sklearn RandomForest training pipeline
│   │   │   ├── alerts.py              # Alert rule evaluation + dispatch (Slack, email)
│   │   │   ├── webhooks.py            # Event firing with HMAC-SHA256 signatures
│   │   │   └── llm.py                 # Gemini + Groq API client with JSON extraction
│   │   │
│   │   └── workers/
│   │       ├── celery_app.py          # Celery application + beat schedule config
│   │       └── tasks.py               # Async tasks: profile, insights, cleaning, report,
│   │                                  #                ingest, train, monitor
│   │
│   ├── migrations/                    # Alembic migrations
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/                  # Migration history
│   │
│   ├── tests/                         # 40+ tests (pytest, offline-safe, no LLM key needed)
│   │   ├── conftest.py                # Engine fixture (SQLite with env overrides)
│   │   ├── test_api.py                # v1 end-to-end flow
│   │   ├── test_v2.py                 # Auth, drift, connectors, training, public API
│   │   ├── test_v34.py                # Teams, annotations, webhooks, model registry, audit, usage
│   │   ├── test_profiler.py           # Profiling service unit tests
│   │   ├── test_quality_checks.py     # Quality check service unit tests
│   │   ├── test_ai_cleaner.py         # AI cleaning recommendation unit tests
│   │   └── test_cleaning_engine.py    # Cleaning transform application unit tests
│   │
│   ├── .env.example                   # Environment template (committed)
│   ├── .env                           # Local config (git-ignored)
│   ├── requirements.txt
│   ├── alembic.ini
│   └── Dockerfile
│
├── frontend/
│   ├── app/                           # 12 Next.js 14 route groups (App Router)
│   │   ├── layout.tsx                 # Root layout + font loading
│   │   ├── page.tsx                   # Cinematic landing page with WebGL + CSV upload
│   │   ├── globals.css                # Design system tokens + component styles
│   │   ├── login/page.tsx
│   │   ├── register/page.tsx
│   │   ├── datasets/
│   │   │   ├── page.tsx               # Dataset list + job status polling
│   │   │   └── [id]/page.tsx          # Dataset detail (7 tabs: overview, quality,
│   │   │                              #   insights, cleaning, charts, report, annotations)
│   │   ├── connectors/page.tsx
│   │   ├── monitor/page.tsx
│   │   ├── training/page.tsx
│   │   ├── teams/page.tsx
│   │   ├── webhooks/page.tsx
│   │   ├── models/page.tsx
│   │   ├── audit/page.tsx
│   │   └── usage/page.tsx
│   │
│   ├── components/                    # 20+ React components
│   │   ├── Nav.tsx                    # Sticky navigation bar
│   │   ├── Footer.tsx
│   │   ├── CinematicCanvas.tsx        # Three.js WebGL canvas (living schema visualization)
│   │   ├── UploadDropzone.tsx         # Drag-and-drop CSV upload
│   │   ├── RequireAuth.tsx            # Auth gate wrapper
│   │   ├── MagneticButton.tsx         # Hover-reactive button (Framer Motion)
│   │   ├── Reveal.tsx                 # Scroll-triggered reveal animation
│   │   ├── CountUp.tsx                # Animated number counter
│   │   ├── HistogramChart.tsx         # Chart.js numeric histogram
│   │   ├── CategoricalBarChart.tsx    # Chart.js categorical bar chart
│   │   ├── AIInsightCard.tsx          # LLM insight display
│   │   ├── CleaningRecommendationCard.tsx
│   │   ├── MissingValueTable.tsx
│   │   ├── OutlierTable.tsx
│   │   ├── JobStatusPoller.tsx        # Poll dataset status until READY
│   │   ├── DatasetListPanel.tsx
│   │   ├── StatCard.tsx
│   │   └── LivingSchema.tsx
│   │
│   ├── lib/
│   │   ├── api.ts                     # Authenticated HTTP client (all endpoints)
│   │   ├── auth.ts                    # Token storage + helpers
│   │   ├── types.ts                   # TypeScript interfaces (all API models)
│   │   ├── config.ts                  # Client-side config
│   │   ├── status.ts                  # Dataset status helpers
│   │   └── scrollStore.ts             # Framer Motion scroll progress store
│   │
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── postcss.config.js
│   └── package.json
│
├── docker-compose.yml                 # 6-service orchestration
├── Dockerfile.frontend                # (referenced by compose)
├── .gitignore
├── run_backend.bat                    # Quick-launch backend script
├── run_frontend.bat                   # Quick-launch frontend script
└── README.md
```

---

## API Overview

### API Versions

| Version | Endpoints | Auth |
|---|---|---|
| **v1** | Upload, profile, insights, cleaning, charts, reports | Public (upload) / JWT |
| **v2** | Auth, connectors, drift, training, alerts, monitoring, public | JWT + API Keys |
| **v3** | Teams, annotations, webhooks | JWT (RBAC) |
| **v4** | Model registry, audit, usage | JWT |

### Authentication

**JWT (sessions):**
```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"securepassword"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"securepassword"}'

# Use token
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

**API Keys (programmatic):**
```bash
# Create a key (JWT required)
curl -X POST http://localhost:8000/api/v1/auth/api-keys \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"name":"ci","scopes":["datasets:read","datasets:write"]}'

# Use key
curl http://localhost:8000/api/v1/public/datasets/<id> \
  -H "X-API-Key: dsk_<key_id>_<secret>"
```

### Key Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/datasets/upload` | Upload CSV (multipart) |
| `GET` | `/api/v1/datasets` | List datasets |
| `GET` | `/api/v1/datasets/{id}` | Dataset status |
| `GET` | `/api/v1/datasets/{id}/profile` | Column profiling results |
| `GET` | `/api/v1/datasets/{id}/insights` | AI column explanations |
| `POST` | `/api/v1/datasets/{id}/insights` | Trigger AI insight generation |
| `GET` | `/api/v1/datasets/{id}/recommendations` | Cleaning recommendations |
| `POST` | `/api/v1/datasets/{id}/recommendations` | Trigger recommendation generation |
| `POST` | `/api/v1/datasets/{id}/cleaning/apply` | Apply selected cleaning transforms |
| `GET` | `/api/v1/datasets/{id}/cleaning/diff` | Before/after diff summary |
| `GET` | `/api/v1/datasets/{id}/download/cleaned` | Download cleaned CSV |
| `GET` | `/api/v1/datasets/{id}/charts/numeric/{col}` | Numeric histogram (10 bins) |
| `GET` | `/api/v1/datasets/{id}/charts/categorical/{col}` | Categorical bar chart (top 10) |
| `GET` | `/api/v1/datasets/{id}/charts/missingness` | Missingness across all columns |
| `POST` | `/api/v1/datasets/{id}/report` | Generate PDF report |
| `GET` | `/api/v1/datasets/{id}/report/download` | Download PDF report |
| `POST` | `/api/v1/drift/snapshots` | Create drift snapshot |
| `POST` | `/api/v1/drift/compare` | Compare two snapshots |
| `POST` | `/api/v1/training` | Start model training job |
| `POST` | `/api/v1/models/{id}/promote` | Promote model stage |
| `POST` | `/api/v1/monitors` | Create monitor schedule |
| `POST` | `/api/v1/monitors/{id}/run` | Run monitor immediately |
| `POST` | `/api/v1/webhooks` | Create webhook |
| `GET` | `/api/v1/audit` | Immutable audit log |
| `GET` | `/api/v1/usage` | API usage metering |

Full interactive documentation at `/docs` (Swagger UI) when the backend is running.

---

## Frontend Routes

| Route | Page |
|---|---|
| `/` | Cinematic landing page with Three.js WebGL canvas + CSV upload dropzone |
| `/login` | JWT login form |
| `/register` | User registration form |
| `/datasets` | Dataset list with job status polling |
| `/datasets/[id]` | Dataset detail with 7 tabs: Overview, Quality, Insights, Cleaning, Charts, Report, Annotations |
| `/connectors` | Manage local/Postgres/S3 data sources |
| `/monitor` | Drift monitoring schedules + run history |
| `/training` | ML training jobs + metric inspection |
| `/teams` | Team CRUD, member invites, role management |
| `/webhooks` | Create webhooks (select events), toggle on/off, delete |
| `/models` | Model registry — filter by stage, promote, view metrics/importances |
| `/audit` | Immutable audit log (paginated, limit selector) |
| `/usage` | API usage metering table with totals |

---

## Data Pipeline

```
┌─────────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐   ┌──────────┐
│ Upload  │──▶│ Profile  │──▶│ Insights │──▶│ Clean   │──▶│ Report   │
│ (CSV)   │   │ (pandas) │   │ (LLM)    │   │ (apply) │   │ (PDF)    │
└─────────┘   └──────────┘   └──────────┘   └─────────┘   └──────────┘
                                     │
                               ┌─────┴──────┐
                               │  Drift     │
                               │  Monitor   │
                               │  (Celery)  │
                               └────────────┘
```

1. **Upload** → Raw CSV saved to disk (`STORAGE_ROOT/{uuid}/raw.csv`), `Dataset` record created with `QUEUED` status
2. **Profile** → `profile_dataset` task: reads CSV, runs pandas profiling (column types, missing%, outliers, skew, cardinality, duplicates), writes `ProfilingResult` → status set to `READY`
3. **AI Insights** → `generate_ai_insights` task: Gemini API (or heuristic fallback) generates column explanations, candidate targets, possible tasks, risks → stored in `AiInsight`
4. **Cleaning** → `generate_cleaning_recommendations` task: detects issues (high missing%, outliers, duplicates, mixed types) → user selects + applies transforms (impute median, drop rows, cap outliers, coerce types) → `CleanedDataset` created
5. **Report** → `generate_report` task: PDF creation with reportlab + matplotlib — overview stats, EDA charts (histograms, bar charts, missingness), quality table, AI insights, cleaning diff
6. **Drift** → Create snapshot baseline → compare against future data or connector pulls → PSI/KS/TVD metrics → trigger alerts + webhooks on threshold breach
7. **Training** → `train_model` task: sklearn RandomForest pipeline → model artifact `.pkl` → registry → promote through `dev` → `staging` → `production`
8. **Monitoring** → `run_due_monitors` beats every 60s → checks all enabled schedules → runs `run_monitor` for any past cadence → stores snapshot + drift comparison → fires alerts + webhooks

---

## Environment Variables

| Variable | Default | Required | Description |
|---|---|---|---|
| `DATABASE_URL` | `sqlite:///./datasentry.db` | No | Database connection string (PostgreSQL for production) |
| `REDIS_URL` | `redis://localhost:6379/0` | No | Celery broker URL |
| `CELERY_EAGER` | `True` | No | Run tasks synchronously (no Redis needed in dev) |
| `ENV` | `development` | No | `production` disables auto-migrations + enforces PostgreSQL |
| `JWT_SECRET` | `change-me-in-production` | **Yes** | HMAC-SHA256 signing key (set to 32+ random chars) |
| `JWT_EXPIRE_MINUTES` | `1440` | No | Token expiry in minutes |
| `ALLOW_SIGNUP` | `True` | No | Allow public registration |
| `GOOGLE_API_KEY` | `""` | No | Gemini API key (heuristic fallback when empty) |
| `GROQ_API_KEY` | `""` | No | Groq API key (fallback LLM provider) |
| `LLM_MODEL` | `gemini-2.0-flash` | No | Gemini model identifier |
| `STORAGE_ROOT` | `./.data` | No | Local disk storage path |
| `MAX_UPLOAD_MB` | `200` | No | Maximum CSV upload size |
| `CORS_ORIGINS` | `http://localhost:3000` | No | Comma-separated allowed origins |
| `SLACK_WEBHOOK_URL` | `""` | No | Slack webhook URL for alerts |
| `SMTP_HOST` | `""` | No | SMTP server for email alerts |
| `SMTP_PORT` | `587` | No | SMTP port |
| `SMTP_USER` | `""` | No | SMTP username |
| `SMTP_PASSWORD` | `""` | No | SMTP password |
| `SMTP_FROM` | `datasentry@localhost` | No | From address for alert emails |

---

## Docker Deployment

```bash
# Full stack with PostgreSQL + Redis
cd datasentry
docker compose up --build

# Services:
#   postgres:5432    — PostgreSQL 16
#   redis:6379       — Redis 7
#   backend:8000     — FastAPI (uvicorn)
#   worker           — Celery worker
#   beat             — Celery Beat (60s tick)
#   frontend:3000    — Next.js
```

**Note:** When using Docker, set `ENV=production` and configure `JWT_SECRET`, `DATABASE_URL`, etc. via Docker environment variables in `docker-compose.yml`.

---

## Testing

```bash
cd backend
.venv\Scripts\python -m pytest -q --timeout=30 tests/
# 40+ tests, ~9s, offline-safe (no LLM API key needed)

# Run specific test file
.venv\Scripts\python -m pytest tests/test_v2.py -q --timeout=30

# Run with coverage
.venv\Scripts\python -m pytest --cov=app tests/

# Run single test
.venv\Scripts\python -m pytest tests/test_v2.py::test_drift_same_data_is_stable -q
```

### Linting & Formatting

```bash
# Backend
.venv\Scripts\python -m black app/ tests/
.venv\Scripts\python -m ruff check app/ tests/

# Frontend
cd frontend && npm run lint
cd frontend && npx tsc --noEmit
```

---

## Security

- **Password hashing**: scrypt (N=16384, r=8, p=1, dklen=64) — stdlib only, no bcrypt dependency
- **JWT**: Hand-implemented HMAC-SHA256 — pure stdlib, no PyJWT dependency
- **API keys**: SHA-256 hashed at rest; plaintext returned once at creation — never stored
- **Webhooks**: Payloads signed with HMAC-SHA256 (`X-DataSentry-Signature` header)
- **Secrets redaction**: Connector credentials redacted in all API responses
- **SQL injection**: Table name validation via regex (alphanumeric + underscore only)
- **Path traversal**: `os.path.abspath` + `os.path.normpath` validation
- **Auth gating**: All endpoints require JWT or API key (except public dataset upload)
- **RBAC**: Team roles enforced at route level (viewer → member → admin → owner)
- **Error handling**: Stack traces never leaked to client (SRS-8.2)

---

## Celery Background Tasks

**Development mode** (`CELERY_EAGER=true` — default):
- Tasks run synchronously when called via `.delay()`
- No Redis required
- All tasks (profile, insights, cleaning, report, ingest, train, monitor) work inline

**Production mode** (`CELERY_EAGER=false`):
```bash
# Terminal 1 — Redis
redis-server

# Terminal 2 — Worker
cd backend && .venv\Scripts\celery -A app.workers.celery_app.celery_app worker --loglevel=info

# Terminal 3 — Beat (scheduled monitors)
.venv\Scripts\celery -A app.workers.celery_app.celery_app beat --loglevel=info
```

The beat schedule runs `run_due_monitors` every 60 seconds, checking all enabled `MonitorSchedule` entries.

---

## Drift Detection

| Metric | Type | Range | Interpretation |
|---|---|---|---|
| **PSI** (Population Stability Index) | Numeric | 0–∞ | <0.1 = stable, 0.1–0.25 = moderate drift, >0.25 = significant drift |
| **KS** (Kolmogorov-Smirnov) | Numeric | 0–1 | Maximum distribution distance |
| **TVD** (Total Variation Distance) | Categorical | 0–1 | Maximum category proportion difference |

All metrics are computed with pure numpy/pandas — no scipy dependency.

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
- [ ] Set `GOOGLE_API_KEY` or `GROQ_API_KEY` for LLM-powered features
- [ ] Configure `SLACK_WEBHOOK_URL` for alert notifications

---

## Key Design Decisions

- **No bcrypt** — password hashing uses stdlib `hashlib.scrypt` (N=16384, r=8, p=1) to eliminate dependencies
- **No PyJWT** — JWT is hand-implemented with `hmac` + `hashlib.sha256` (stdlib only)
- **No scipy** — drift detection (PSI, KS, TVD) is pure numpy/pandas
- **SQLite-compatible booleans** — `enabled`, `active`, `delivered` columns use `"true"`/`"false"` strings
- **Top-level imports** — no inline or dynamic imports; all modules import at module level
- **Local-first** — everything runs locally by default; data never leaves the machine unless configured otherwise

---

## License

MIT
