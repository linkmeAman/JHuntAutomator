import logging
from typing import List, Dict, Any

SOURCE_ID = "glassdoor"
logger = logging.getLogger(__name__)


def fetch_jobs(settings) -> List[Dict[str, Any]]:
    logger.warning("Glassdoor source is restricted; returning no jobs.")
    return []
