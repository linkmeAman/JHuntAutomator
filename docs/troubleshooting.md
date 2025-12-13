# Troubleshooting

## TLS / SSL certificate errors
- Symptom: `CERTIFICATE_VERIFY_FAILED` when calling sources like TimesJobs.
- Fixes:
  - Ensure CA bundles are present; Python `certifi` bundle is used by default.
  - Environment overrides supported: `REQUESTS_CA_BUNDLE`, `SSL_CERT_FILE`, `SSL_CERT_DIR`.
  - Update system CA certificates or install missing corporate root CAs.
  - After fixing, retry or run `/api/crawl/debug-run` with `{"ignore_cooldown": true}` to bypass cooldown.

## Cooldown / skipped sources
- Sources enter cooldown after repeated transient failures, rate limits, or explicit block errors.
- Cooldown is stored in the `source_state` table; it expires automatically.
- For one-off testing, call `/api/crawl/debug-run` with `ignore_cooldown=true`.
