# Project Change Summary

## Backend Enhancements
- Added robust URL canonicalization and `job_key` for deduplication (source + canonical URL; fallback to title/company/location/date). Keeps legacy `job_hash` for compatibility.
- Schema ensure adds `job_key`, `remote`, `source_meta`, and `source_metrics` columns with unique index on `job_key`.
- Crawl pipeline supports dry-run/debug runs, optional source overrides, configurable max pages, and stores per-source metrics (parsed, scored, deduped, inserted, errors). `CrawlResult` returns `run_id`.
- Added debug endpoint `POST /api/crawl/debug-run` for targeted dry runs (dev use); no inserts when `dry_run=true`.
- Scoring no longer drops low-score jobs; `MIN_SCORE_TO_STORE` default 0.0 (store all, filter later).

## LinkedIn Integration (Compliant)
- Email-based ingestion via IMAP; optional Gmail stub. Source obeys `LINKEDIN_MODE` (email default; whitelist crawl only if allowed flag set).
- Settings include LinkedIn mode/email/crawl config; sources include `linkedin`.

## Settings & Defaults
- New defaults for broader fetch: `MAX_PAGES_PER_SOURCE=5`, request delay jitter, `MIN_SCORE_TO_STORE=0.0`.
- Settings schema includes `india_mode`, `linkedin_mode`, `linkedin_email`, `linkedin_crawl`.

## Frontend UX Redesign (No Backend Changes)
- Sidebar navigation: Overview, Jobs, Activity, Sources, Preferences, Integrations (collapsible/drawer).
- Overview: hero stats, last crawl health, “Run Job Scan” CTA, dedupe explanation.
- Jobs: sticky filters (search/location/source/status/score), relevance meter, matched skills, detail drawer.
- Activity: recent runs with fetched/new/deduped and microcopy explaining “0 new.”
- Sources: grouped cards with toggles and helper text.
- Preferences: cards for keywords, locations, schedule.
- Integrations: LinkedIn steps (email-first, compliance).
- Inputs restyled for clarity; job fetch adds cache-busting param to avoid stale lists.

## Tests
- Dedupe and scoring: different URLs produce different `job_key`; low-score jobs still stored.
- LinkedIn: email parsing fixture; crawl refusal when not allowed.
- Existing parser/dedupe tests retained.

## How to Run (Local)
- Backend: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- API: `CRAWL_MODE=workflow python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000`
- One-off crawl: `python -m backend.runner`
- Frontend: `npm install --prefix frontend && npm run dev --prefix frontend`
- Debug (dev): `POST /api/crawl/debug-run` with `{"sources":["remoteok"],"dry_run":true}`

## Notes
- No breaking API changes; additive only.
- No live scraping in tests; fixtures/mocks used.
- Compliant LinkedIn ingestion; whitelist crawl guarded by explicit allow flag.
