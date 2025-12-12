# Project Overview

- **Name**: Zero-Cost Automated IT Job Discovery  
- **Stack**: Python 3.11 (FastAPI, SQLAlchemy, APScheduler), SQLite (default), Node.js/Next.js 16 + React 19 (frontend), Tailwind 4 styles, Axios client. Optional NLP via `sentence-transformers`.

# Backend (FastAPI)

- **Core APIs**: Jobs listing/filtering, job detail/update, manual crawl (`/api/rescan` + alias), settings get/update (keywords, locations, source flags, Greenhouse boards, schedule), stats, healthcheck (`/health`), crawl runs list/detail.
- **Crawlers**: RemoteOK, WeWorkRemotely (RSS), Greenhouse JSON (configurable boards), Indeed (opt-in, disabled by default, warns on use). Keyword + semantic scoring; deterministic SHA-256 job hash per source/title/company/url.
- **Pipeline**: Loads runtime settings from DB, runs enabled sources, dedupes by hash, bulk inserts new jobs, records crawl runs (attempted/succeeded/failed, counts, durations), optional notifications.
- **Scheduling**: `CRAWL_MODE=server` starts APScheduler on startup; `workflow` skips scheduler (default). Manual crawl always available.
- **DB**: SQLite with WAL + busy_timeout, schema ensured on init; indexes for hash, score, created_at, applied, source, and crawl run timestamps.
- **Notifications**: Optional email/Telegram digests (thresholded) and alerts for source failures/zero-new jobs; fails are non-blocking.

# Frontend (Next.js)

- **Dashboard**: Job cards with relevance scores, applied status, matched keywords, search/location/status filters, rescan trigger.
- **Job Detail**: Applied toggle, external apply link, notes editor, metadata display.
- **Settings**: Manage keywords, locations, source toggles, schedule, and Greenhouse boards (add/remove UI).
- **Runs View**: Recent crawl runs with counts, duration, and failures summary.
- **API Client**: Axios with typed DTOs; honors `NEXT_PUBLIC_API_URL`.

# Ops & Tooling

- **Tests**: Pytest smoke coverage for scoring, crawlers (RSS/Greenhouse fixtures, cached HTTP), DB dedupe/indexing, scheduler gating, crawl run persistence, notification gating.
- **CI**: `.github/workflows/daily-crawl.yml` installs deps, runs pytest, and executes `python -m backend.runner` with `CRAWL_MODE=workflow` on schedule/dispatch.
- **Env/Secrets**: Keep SMTP/Telegram/profile secrets in env or GitHub Actions secrets only; defaults stored in `backend/config.py`.

# Run Commands (local)

- Backend install: `python -m pip install --upgrade pip && pip install -r requirements.txt`
- Backend run (no scheduler): `CRAWL_MODE=workflow python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000`
- Backend run (with scheduler): `CRAWL_MODE=server python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000`
- One-off crawl: `python -m backend.runner`
- Frontend install: `npm install --prefix frontend`
- Frontend run: `npm run dev --prefix frontend` (set `NEXT_PUBLIC_API_URL` if backend not at `http://localhost:8000`)
