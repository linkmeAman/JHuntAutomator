import logging
import random
import time
from typing import List, Dict, Any

from backend.linkedin_email_ingest import fetch_via_imap, parse_eml
from backend.http_client import get, SourceBlockedError

SOURCE_ID = "linkedin"
logger = logging.getLogger(__name__)


def fetch_jobs(settings) -> List[Dict[str, Any]]:
    mode = getattr(settings, "LINKEDIN_MODE", "email")
    if mode == "email":
        return fetch_jobs_via_email(settings)
    return fetch_jobs_via_whitelist(settings)


def fetch_jobs_via_email(settings) -> List[Dict[str, Any]]:
    config = getattr(settings, "LINKEDIN_EMAIL", {})
    jobs = fetch_via_imap(config)
    for job in jobs:
        job["source"] = SOURCE_ID
    return jobs


def fetch_jobs_via_whitelist(settings) -> List[Dict[str, Any]]:
    crawl_cfg = getattr(settings, "LINKEDIN_CRAWL", {})
    allowed = crawl_cfg.get("allowed", False)
    if not allowed:
        logger.warning("LinkedIn crawl not allowed; set LINKEDIN_CRAWL_ALLOWED=true after whitelisting.")
        return []

    seed_urls = [u for u in crawl_cfg.get("seed_urls", []) if u.strip()]
    max_pages = crawl_cfg.get("max_pages", 2)
    min_delay = max(3, crawl_cfg.get("min_delay_sec", 3))
    jobs: List[Dict[str, Any]] = []

    for url in seed_urls[:max_pages]:
        try:
            time.sleep(min_delay + random.uniform(0.2, 0.8))
            resp = get(url, timeout=(10, 30))
            text = resp.text.lower()
            if any(tok in text for tok in ["captcha", "verify", "access denied"]):
                raise SourceBlockedError("Blocked by LinkedIn")
            # We do not parse LinkedIn HTML content to avoid ToS issues; store link only.
            jobs.append(
                {
                    "title": "LinkedIn Listing",
                    "company": "",
                    "location": "",
                    "description": "LinkedIn search result",
                    "url": url,
                    "source": SOURCE_ID,
                    "remote": False,
                    "source_meta": {"seed_url": url},
                }
            )
        except SourceBlockedError as exc:
            logger.warning("LinkedIn blocked: %s", exc)
        except Exception as exc:
            logger.error("LinkedIn crawl failed: %s", exc)

    return jobs
