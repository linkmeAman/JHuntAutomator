import logging
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from backend.http_client import get, SourceBlockedError

SOURCE_ID = "naukri"
logger = logging.getLogger(__name__)


def parse_jobs(html: str) -> List[Dict[str, Any]]:
    jobs: List[Dict[str, Any]] = []
    soup = BeautifulSoup(html, "lxml")
    if soup.find(string=lambda x: x and "captcha" in x.lower()):
        raise SourceBlockedError("Naukri appears blocked")
    for card in soup.select("article"):
        title_el = card.select_one("a.title") or card.select_one("a[href]")
        title = title_el.get_text(strip=True) if title_el else ""
        url = title_el["href"] if title_el and title_el.has_attr("href") else ""
        company_el = card.select_one(".comp-name") or card.select_one(".company-name")
        company = company_el.get_text(strip=True) if company_el else ""
        location_el = card.select_one(".loc") or card.select_one(".location")
        location = location_el.get_text(strip=True) if location_el else ""
        desc_el = card.select_one(".job-desc") or card.select_one("p")
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
    query = (settings.DEFAULT_KEYWORDS[0] if settings.DEFAULT_KEYWORDS else "software").replace(" ", "+")
    url = f"https://www.naukri.com/{query}-jobs"
    try:
        resp = get(url)
        if resp.status_code != 200:
            logger.warning("Naukri responded with %s", resp.status_code)
            return []
        return parse_jobs(resp.text)
    except SourceBlockedError as exc:
        logger.warning("Naukri blocked: %s", exc)
    except Exception as exc:
        logger.error("Naukri fetch failed: %s", exc)
    return []
