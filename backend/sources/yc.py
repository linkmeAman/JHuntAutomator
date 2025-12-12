import logging
from typing import List, Dict, Any

SOURCE_ID = "yc"
logger = logging.getLogger(__name__)


def fetch_jobs(settings) -> List[Dict[str, Any]]:
    logger.warning("YC WorkAtAStartup source is restricted; returning no jobs.")
    return []
