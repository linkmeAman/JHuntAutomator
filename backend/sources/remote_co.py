import logging
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from backend.http_client import get, SourceBlockedError

SOURCE_ID = "remote_co"
logger = logging.getLogger(__name__)


def parse_jobs(html: str) -> List[Dict[str, Any]]:
    jobs: List[Dict[str, Any]] = []
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True).lower()
    if "captcha" in text or "verify you are human" in text or "access denied" in text:
        raise SourceBlockedError("Remote.co appears blocked")

    for card in soup.select("li.card"):
        title_el = card.select_one("a")
        title = title_el.get_text(strip=True) if title_el else ""
        url = title_el["href"] if title_el and title_el.has_attr("href") else ""
        company_el = card.select_one(".company")
        company = company_el.get_text(strip=True) if company_el else ""
        location_el = card.select_one(".location") or card.select_one(".tag")
        location = location_el.get_text(strip=True) if location_el else "Remote"
        desc_el = card.select_one("p") or card.select_one(".description")
        description = desc_el.get_text(" ", strip=True) if desc_el else title
        if title and url:
            jobs.append(
                {
                    "title": title,
                    "company": company,
                    "location": location,
                    "description": description,
                    "url": url,
                    "source": SOURCE_ID,
                    "remote": True,
                }
            )
    return jobs


def fetch_jobs(settings) -> List[Dict[str, Any]]:
    url = "https://remote.co/remote-jobs/developer/"
    try:
        resp = get(url)
        if resp.status_code != 200:
            logger.warning("Remote.co responded with %s", resp.status_code)
            return []
        return parse_jobs(resp.text)
    except SourceBlockedError as exc:
        logger.warning("Remote.co blocked: %s", exc)
    except Exception as exc:
        logger.error("Remote.co fetch failed: %s", exc)
    return []
