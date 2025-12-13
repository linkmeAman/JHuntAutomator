# Crawling Compliance Guide

## Allowed
- API and RSS endpoints.
- Public HTML pages that do not require login and are permissible per robots/terms.
- Broad fetch with local filtering (store all, score later).

## Disallowed
- Login automation, CAPTCHA solving, stealth/fingerprint evasion.
- Scraping behind access controls or in violation of site terms.

## Adding a Source (module)
- Export `SOURCE_ID` and `fetch_jobs(settings, cursor_info=None)` returning list of dicts with: title, company, location, description, url, source, post_date (if available), remote (bool), source_meta (optional).
- Use `generate_queries` for search sources; honor `settings.CRAWL_MAX_QUERIES_PER_SOURCE`.
- Apply minimal server-side filters; rely on local scoring.
- Record block indicators with `SourceBlockedError`; throw specific errors for TLS/rate/blocked/bad-config.

## Cursor Usage
- Read `cursor_info` for `last_max_post_date_seen`, `next_page_token`, `http_cache` (etag/last_modified) if provided.
- Advance `last_max_post_date_seen` to the newest post_date observed (even if deduped).
- Store `etag`/`last_modified` when available.

## Metrics Expectations
- Increment: fetched_count, jobs_parsed_count, jobs_normalized_count, jobs_scored_count, matched_count, jobs_inserted_count, jobs_updated_count, jobs_deduped_count.
- Set `not_modified=True` when HTTP 304.
- Log stop-on-seen ratio when > configured threshold.

## Troubleshooting “0 new”
- Check cooldown/skipped sources (logs/app.log).
- Inspect `source_metrics` for high dedupe/stop_on_seen_ratio.
- Verify `last_max_post_date_seen` advanced and lookback covers recent days.
- Use `/api/crawl/debug-run` with `ignore_cooldown=true` to force a run for diagnostics (no live scraping in tests).
