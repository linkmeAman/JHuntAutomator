import logging
from typing import List, Dict, Any

import requests

SOURCE_ID = "workingnomads"
API_URL = "https://www.workingnomads.com/api/exposed_jobs/"
logger = logging.getLogger(__name__)


def fetch_jobs(settings) -> List[Dict[str, Any]]:
    jobs: List[Dict[str, Any]] = []
    try:
        resp = requests.get(API_URL, timeout=10)
        if resp.status_code != 200:
            logger.warning("WorkingNomads responded with %s", resp.status_code)
            return jobs
        data = resp.json()
        for item in data or []:
            title = item.get("title") or ""
            company = item.get("company_name") or ""
            url = item.get("url") or ""
            description = item.get("description") or title
            location = item.get("location") or "Remote"
            category = item.get("category_name")
            tags = item.get("tags") or []
            pub_date = item.get("pub_date")
            job_id = item.get("id")

            jobs.append(
                {
                    "title": title,
                    "company": company,
                    "location": location,
                    "description": description,
                    "url": url,
                    "source": SOURCE_ID,
                    "post_date": pub_date,
                    "remote": True,
                    "source_meta": {
                        "category": category,
                        "tags": tags,
                        "wn_id": job_id,
                    },
                }
            )
    except Exception as exc:
        logger.error("WorkingNomads fetch failed: %s", exc)
    return jobs
