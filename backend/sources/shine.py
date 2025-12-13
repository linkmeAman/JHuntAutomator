import logging
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from backend.http_client import get, SourceBlockedError
from backend.crawl_engine.query_utils import generate_queries

SOURCE_ID = "shine"
logger = logging.getLogger(__name__)


def parse_jobs(html: str) -> List[Dict[str, Any]]:
    jobs: List[Dict[str, Any]] = []
    soup = BeautifulSoup(html, "lxml")
    if soup.find(string=lambda x: x and "captcha" in x.lower()):
        raise SourceBlockedError("Shine appears blocked")
    for card in soup.select("li"):
        title_el = card.select_one("a")
        title = title_el.get_text(strip=True) if title_el else ""
        url = title_el["href"] if title_el and title_el.has_attr("href") else ""
        company_el = card.select_one(".jobListCompanyName") or card.select_one(".jobCardCompanyName")
        company = company_el.get_text(strip=True) if company_el else ""
        location_el = card.select_one(".jobCardLocation") or card.select_one(".jobListLocation")
        location = location_el.get_text(strip=True) if location_el else ""
        desc_el = card.select_one(".jobCardDesc")
        description = desc_el.get_text(" ", strip=True) if desc_el else title
        if title and url:
            jobs.append(
                {
                    "title": title,
                    "company": company,
                    "location": location or "India",
                    "description": description,
                    "url": url,
                    "source": SOURCE_ID,
                    "remote": False,
                }
            )
    return jobs


def fetch_jobs(settings) -> List[Dict[str, Any]]:
    queries = generate_queries(
        settings.DEFAULT_KEYWORDS,
        settings.INDIA_MODE,
        settings.CRAWL_MAX_QUERIES_PER_SOURCE,
        settings.CRAWL_QUERY_VARIANTS,
    )
    results: List[Dict[str, Any]] = []
    for query in queries:
        search = query.replace(" ", "-")
        url = f"https://www.shine.com/job-search/{search}-jobs"
        try:
            resp = get(url)
            if resp.status_code != 200:
                logger.warning("Shine responded with %s", resp.status_code)
                continue
            results.extend(parse_jobs(resp.text))
        except SourceBlockedError as exc:
            logger.warning("Shine blocked: %s", exc)
            break
        except Exception as exc:
            logger.error("Shine fetch failed: %s", exc)
    deduped = []
    seen = set()
    for job in results:
        if job["url"] in seen:
            continue
        seen.add(job["url"])
        deduped.append(job)
    return deduped
