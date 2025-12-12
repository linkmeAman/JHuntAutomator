import logging

from .crawl_runner import execute_crawl
from .database import SessionLocal, init_db
from .main import init_default_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_once() -> None:
    """Initialize the DB (if needed) and execute one crawl cycle."""
    init_db()
    db = SessionLocal()
    try:
        init_default_settings(db)
        result = execute_crawl(db, send_notifications=True)
        logger.info(result.message)
    finally:
        db.close()


if __name__ == "__main__":
    run_once()
