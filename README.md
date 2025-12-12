# Zero-Cost Automated IT Job Discovery

This workspace hosts a full-stack system that crawls multiple job boards, enriches the results with NLP-based relevance scoring, stores them in SQLite, and surfaces them through a Next.js dashboard. The backend exposes FastAPI endpoints, schedules daily crawls, and can optionally send SMTP and Telegram digests.

## How to Run (Backend + Frontend)

### Prerequisites
- Python 3.11+
- Node.js 18+
- SQLite (bundled). Override with `DATABASE_URL` for Postgres or others.

### Backend (FastAPI)
1) Install dependencies
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```
2) Run the API
```bash
# Workflow mode (no scheduler; good for CI/local testing)
CRAWL_MODE=workflow python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Server mode (starts APScheduler)
CRAWL_MODE=server python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
3) One-off crawl without running the server
```bash
python -m backend.runner
```

Handy endpoints:
- `GET /health` — scheduler mode, DB connectivity, last crawl summary
- `POST /api/rescan` (alias `/api/crawl/rescan`) — manual crawl
- `GET/PUT /api/settings` — update keywords, locations, source flags, Greenhouse boards, schedule
- `GET /api/jobs` — list jobs with filters

### Frontend (Next.js Dashboard)
1) Install dependencies
```bash
npm install --prefix frontend
```
2) Start dev server (defaults to port 5000)
```bash
npm run dev --prefix frontend
```
Set `NEXT_PUBLIC_API_URL` if the backend is not at `http://localhost:8000`.

### Full-Stack Dev
- Unix/macOS: `./start.sh` (backend on 8000, frontend on 5000)
- Windows (PowerShell):
  ```powershell
  cd backend; $env:CRAWL_MODE="workflow"; python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
  cd ..\frontend; npm run dev
  ```

### Quick Commands (copy/paste)
- Backend install: `python -m pip install --upgrade pip && pip install -r requirements.txt`
- Backend run (no scheduler): `CRAWL_MODE=workflow python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000`
- Backend run (with scheduler): `CRAWL_MODE=server python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000`
- One-off crawl: `python -m backend.runner`
- Frontend install: `npm install --prefix frontend`
- Frontend run: `npm run dev --prefix frontend` (set `NEXT_PUBLIC_API_URL` if backend isn’t at `http://localhost:8000`)

### Notes
- Default DB: `jobs.db` (SQLite). Adjust `DATABASE_URL` as needed.
- Profile text: `PROFILE_TEXT` or `PROFILE_TEXT_PATH`.
- Source flags defaults: `ENABLE_INDEED=false`, `ENABLE_REMOTEOK=true`, `ENABLE_WEWORKREMOTELY=true`, `ENABLE_GREENHOUSE=true`.
- Keep secrets only in env vars or GitHub Actions encrypted secrets—never commit them.

## NLP Relevance Scoring

Sentence-transformer embeddings run locally to score each listing against your profile. Configure a profile summary via either:

- `PROFILE_TEXT` (string secret/env var), or
- `PROFILE_TEXT_PATH` pointing to a local text file.

You can fine-tune the behavior with:

- `NLP_MODEL_NAME` (default `sentence-transformers/all-MiniLM-L6-v2`)
- `NLP_WEIGHT` (float multiplier applied to the semantic score)

If no profile text is provided or the dependency is missing, the system gracefully falls back to keyword scoring.

## Notifications

Enable digests by exporting `ENABLE_NOTIFICATIONS=true` along with one or both channel configs below.

Keep SMTP/Telegram credentials only in environment variables or GitHub Actions encrypted secrets—never commit secrets to the repo.

**Email (SMTP):**

- `ENABLE_EMAIL_NOTIFICATIONS=true`
- `SMTP_HOST`, `SMTP_PORT`
- `SMTP_USERNAME`, `SMTP_PASSWORD`
- `EMAIL_SENDER`, `EMAIL_RECIPIENT`

**Telegram:**

- `ENABLE_TELEGRAM_NOTIFICATIONS=true`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Filter the digest to only high-quality matches by adjusting `NOTIFICATION_MIN_SCORE` (default `3.0`).

## GitHub Actions Automation

The workflow in `.github/workflows/daily-crawl.yml` runs on each push/PR and on a daily cron. Scheduled runs install backend deps, execute tests, and then call `python -m backend.runner` so you get a fresh batch without keeping a personal machine online.

Create the following repository secrets to make the workflow fully autonomous:

| Secret | Purpose |
| --- | --- |
| `PROFILE_TEXT` | Resume/Profile summary for semantic scoring (or use `PROFILE_TEXT_PATH` in Actions variables). |
| `ENABLE_NOTIFICATIONS`, `ENABLE_EMAIL_NOTIFICATIONS`, `ENABLE_TELEGRAM_NOTIFICATIONS` | Feature flags for digests (set to `"true"`/`"false"`). |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_SENDER`, `EMAIL_RECIPIENT` | Email delivery via SMTP. |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Telegram delivery. |

If you prefer a custom database, also provide `DATABASE_URL`. Secrets that are irrelevant (e.g., Telegram when you only email) can be omitted.

## Tests

Simple smoke tests live under `tests/` and are executed via `pytest`. Extend this suite as you add new sources or business rules so regressions are caught before deployment.
