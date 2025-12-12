import logging
from typing import List, Dict, Any

SOURCE_ID = "wellfound"
logger = logging.getLogger(__name__)


def fetch_jobs(settings) -> List[Dict[str, Any]]:
    logger.warning("Wellfound source is restricted; returning no jobs.")
    return []
