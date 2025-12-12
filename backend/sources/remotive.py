import logging
from typing import List, Dict, Any

import requests

SOURCE_ID = "remotive"
API_URL = "https://remotive.com/api/remote-jobs"
logger = logging.getLogger(__name__)


def fetch_jobs(settings) -> List[Dict[str, Any]]:
    jobs: List[Dict[str, Any]] = []
    try:
        resp = requests.get(API_URL, timeout=10)
        if resp.status_code != 200:
            logger.warning("Remotive responded with %s", resp.status_code)
            return jobs
        data = resp.json()
        for item in data.get("jobs", []):
            title = item.get("title") or ""
            company = item.get("company_name") or ""
            url = item.get("url") or ""
            description = item.get("description") or title
            location = item.get("candidate_required_location") or "Remote"
            category = item.get("category")
            job_type = item.get("job_type")
            publication_date = item.get("publication_date")
            job_id = item.get("id")

            jobs.append(
                {
                    "title": title,
                    "company": company,
                    "location": location,
                    "description": description,
                    "url": url,
                    "source": SOURCE_ID,
                    "post_date": publication_date,
                    "remote": True,
                    "source_meta": {
                        "category": category,
                        "job_type": job_type,
                        "remotive_id": job_id,
                    },
                }
            )
    except Exception as exc:
        logger.error("Remotive fetch failed: %s", exc)
    return jobs
