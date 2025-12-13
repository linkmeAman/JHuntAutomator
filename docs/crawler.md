# Crawler Architecture (Current)

## Sources
- **API-based**: RemoteOK, Remotive, WorkingNomads, Greenhouse boards, LinkedIn (email ingestion by default).
- **HTML-based**: WeWorkRemotely (RSS), Remote.co, Naukri, Shine, TimesJobs.
- **Restricted placeholders**: Glassdoor, Wellfound, YC (return [] with warning).
- Indeed remains opt-in, with warning.
- Cooldowns: failing sources back off automatically (default 15 minutes); state persisted in `source_state` to avoid hammering blocked sites.

## Settings & Controls
- Enabled sources merge env defaults (`backend/config.py`) with DB settings (`settings` table). India portals default off; LinkedIn default off unless configured. Remotive/WorkingNomads default on; Remote.co default on.
- Key knobs:
  - `MAX_PAGES_PER_SOURCE` (default 5) — page hint.
  - `MAX_JOBS_PER_SOURCE` (default 200) — cap after parsing.
  - Request delay jitter: 600–1200 ms.
  - `MIN_SCORE_TO_STORE` (default 0.0) — store all jobs regardless of score; score used for ordering/notifications.
  - LinkedIn modes: `LINKEDIN_MODE` (email | whitelist_crawl), `LINKEDIN_CRAWL_ALLOWED` gate.

## Execution Flow (Engine v2 default)
1. Load settings from DB (keywords, locations, sources, greenhouse boards, LinkedIn configs).
2. Initialize NLP scorer (if available/profile provided) and Engine v2 orchestrator.
3. Iterate enabled sources (concurrent, threaded for legacy sync sources):
   - Fetch jobs (API/HTML). HTML uses shared http_client (UA, retries, jitter) or legacy crawler; API calls go through `httpx`.
   - Normalize fields: title, company, location, url, source, post_date, remote, source_meta.
   - Score locally (keyword + optional semantic).
   - Compute `job_key` (source + canonical URL preferred; fallback title/company/location/date) and `job_fingerprint` for change detection; legacy `job_hash` retained.
   - Collect per-source metrics (parsed, scored, deduped, inserted attempts, errors).
4. Deduplication uses `job_key` uniqueness; existing rows skipped; if fingerprint changes, job is updated and `last_seen_at` refreshed.
5. Persistence: in non-dry runs, bulk-save new jobs; update changed jobs; low scores still stored. source_meta serialized to JSON text.
6. Run record: `crawl_runs` row stores attempted/succeeded/failed sources, fetched count, inserted_new_count, duration, `source_metrics` JSON (per-source stats), and tracks cooldown/seen state.
7. State: `source_state` table records cursors (reserved), last_success_at, failures, cooldown_until to drive backoff.
8. Notifications: if enabled and not dry-run, sends digests/alerts after inserts.
9. Return: `CrawlResult` with counts and `run_id`. Set `CRAWL_ENGINE=v1` to use legacy pipeline.

## Diagnostics & Debugging
- Per-run metrics (`crawl_runs.source_metrics`): requested_pages (hint), pages_fetched (reserved), http_status_counts (reserved), jobs_parsed_count, jobs_scored_count, jobs_above_threshold_count, jobs_insert_attempted_count, jobs_inserted_count, jobs_deduped_count, errors[].
- Endpoint `/api/crawl/debug-run` (dev/internal): body `{ sources: [...], max_pages, dry_run }`; returns metrics; no inserts when `dry_run=true`.
- Health/cooldown checks: `source_state.cooldown_until` indicates when a failing source will resume; delete/adjust rows only if you intentionally want to force a retry.

## Rescan
- `/api/rescan` triggers a full crawl with current settings, returns `run_id` (Engine v2 runs inside its own event loop/thread).
- `/api/runs/{run_id}` (and list) available for polling/inspection.

## LinkedIn (Compliant)
- Email mode: IMAP fetch via `linkedin_email_ingest.py`, parses alert emails for links/titles; no LinkedIn page fetch.
- Whitelist crawl mode: only if `LINKEDIN_CRAWL_ALLOWED=true`; uses provided seed URLs; aborts on block indicators.

## Dedupe Details
- Canonical URL strips tracking params (utm_*), keeps ID-like queries; lowercase, trim trailing slash.
- If URL missing, fallback hash uses title/company/location/post_date + source.

## Error Handling
- `SourceBlockedError` for HTML sources; logged and recorded in metrics; run continues.
- Transaction commits only when not dry-run; errors roll back and are recorded in run entry.
- Network/SSL timeouts are logged and push the source into cooldown; resume automatically after cooldown expires.
