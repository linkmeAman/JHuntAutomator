# Crawler Engine v2

## Architecture
Pipeline: Fetcher → Parser → Normalizer → Dedupe → Persist, with per-source metrics and state.

### Components
- **Fetcher (async, httpx)**: global/per-domain rate limits, jittered delay, retries. Used mainly to enable concurrency scaffolding; legacy sources run in thread pool until migrated.
- **Parser**: source modules return RawJobs; soft failures recorded.
- **Normalizer**: canonical URL, schema validation via Pydantic; builds job_key/hash/fingerprint.
- **Dedupe/Identity**: job_key (source + canonical URL fallback title/company/location/date), job_fingerprint (content hash) to detect updates; upsert-like behavior updates fields/last_seen_at when fingerprint changes.
- **Persist**: bulk insert new; update existing on fingerprint change; track last_seen_at.
- **State**: `source_state` table stores cursor_json (last_max_post_date_seen, http_cache placeholders), last_success_at, consecutive_failures, cooldown_until. Circuit breaker via cooldown.
- **Metrics**: per-source stats (parsed, scored, deduped, inserted, errors); stored in crawl_runs.source_metrics.

## Incremental Crawling
- `source_state` persists cursors and cooldowns; adapter currently uses basic state (no native API cursors yet).
- Stop-early logic can be layered via stop_on_seen_ratio once sources emit cursors; cooldown triggers on repeated failures.

## Concurrency & Safety
- Async engine with thread offloading for legacy sync sources; global/per-domain semaphores; jittered delays; circuit breaker via cooldown.

## Freshness Controls (defaults)
- MAX_PAGES_PER_SOURCE=5, MAX_JOBS_PER_SOURCE=200, jitter 600–1200ms.
- MIN_SCORE_TO_STORE=0.0 (store all; score for ordering/notifications).
- crawl.mode (broad/focused) placeholder retained via settings (not yet enforced per source).

## Observability
- Metrics in `crawl_runs.source_metrics`: parsed, scored, above_threshold, insert_attempted, inserted, deduped, errors. Errors now include cooldown reasons and stop-on-seen hints.
- Debug endpoint `/api/crawl/debug-run` for dry-run metrics (no inserts). Pass `{"ignore_cooldown": true}` to bypass cooldown for troubleshooting.
- Runs expose run_id for polling.

## Data Hygiene
- Adds job_fingerprint, last_seen_at; updates existing rows on fingerprint change; keeps dedupe on job_key.

## How to Add a Source Plugin (incremental)
1. Implement `build_requests(settings, cursor)` (planned) or provide `fetch_jobs(settings)` returning list of dicts.
2. Return RawJob-like dicts with title/company/location/url/source/post_date.
3. Engine handles normalization, dedupe, persistence.
4. If source supports cursors, store cursor in `source_state.cursor_json` and advance per run.

## Tuning Knobs
- Concurrency: global 10, per-domain 2 (Fetcher).
- Delays: REQUEST_DELAY_MS_MIN/MAX.
- Pagination: MAX_PAGES_PER_SOURCE, MAX_JOBS_PER_SOURCE.
- Scoring: MIN_SCORE_TO_STORE (store threshold), notifications threshold separate.
- Engine select: CRAWL_ENGINE=v2|v1 (v2 default).
