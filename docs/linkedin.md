# LinkedIn Integration (Email-first, Compliant)

## Mode A: Job Alerts via Email (Recommended)
1. Create LinkedIn job alerts for your keywords/locations.
2. Set delivery to an inbox you control (IMAP/Gmail).
3. Configure env/settings:
   - `ENABLE_LINKEDIN=true`
   - `LINKEDIN_MODE=email`
   - IMAP: `LINKEDIN_IMAP_HOST`, `LINKEDIN_IMAP_PORT` (default 993), `LINKEDIN_IMAP_USERNAME`, `LINKEDIN_IMAP_PASSWORD_ENV` (stores password in env), `LINKEDIN_EMAIL_QUERY` (default targets LinkedIn Job Alerts), `LINKEDIN_MAX_EMAILS_PER_RUN` (default 30).
   - Gmail API (optional): implement OAuth in `backend/gmail_client.py` and pipe messages to `linkedin_email_ingest.parse_eml`.
4. The system parses alert emails, extracts job links/titles, and stores them as jobs. It never fetches LinkedIn job pages.

## Mode B: Whitelisted Crawl (Optional, Off by Default)
- Set `LINKEDIN_MODE=whitelist_crawl` and `LINKEDIN_CRAWL_ALLOWED=true` only after obtaining explicit permission from LinkedIn (robots references whitelisting contact).
- Provide your own `LINKEDIN_SEED_URLS` (comma-separated) to crawl; no discovery.
- Hard rate limits; if blocked/redirected/captcha detected, the source aborts and logs a warning.

## Notes
- Default: `ENABLE_LINKEDIN=false`, mode=email, crawl allowed=false.
- LinkedIn Talent APIs are for job posting/integration, not for marketplace crawling. Only ingest alerts you receive or crawl with explicit approval.
