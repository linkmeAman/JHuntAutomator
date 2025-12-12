from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
import json

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def scheduled_crawl(app):
    """Function to run scheduled job crawl"""
    logger.info("Starting scheduled job crawl...")
    
    from .crawl_runner import execute_crawl
    from .database import SessionLocal
    
    db = SessionLocal()
    try:
        result = execute_crawl(db, send_notifications=True)
        logger.info(
            "Scheduled crawl complete: %s",
            result.message,
        )
    except Exception as e:
        logger.error(f"Error during scheduled crawl: {e}")
    finally:
        db.close()

def start_scheduler(app):
    """Start the background scheduler"""
    from .database import SessionLocal
    from .models import Settings as SettingsModel
    from .config import settings
    
    db = SessionLocal()
    try:
        schedule_setting = db.query(SettingsModel).filter(SettingsModel.key == "schedule").first()
        if schedule_setting:
            schedule_data = json.loads(schedule_setting.value)
            hour = schedule_data.get("hour", settings.CRAWL_SCHEDULE_HOUR)
            minute = schedule_data.get("minute", settings.CRAWL_SCHEDULE_MINUTE)
        else:
            hour = settings.CRAWL_SCHEDULE_HOUR
            minute = settings.CRAWL_SCHEDULE_MINUTE
        
        scheduler.add_job(
            scheduled_crawl,
            CronTrigger(hour=hour, minute=minute),
            args=[app],
            id='daily_job_crawl',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info(f"Scheduler started: Daily crawl at {hour:02d}:{minute:02d}")
        
    finally:
        db.close()

def stop_scheduler():
    """Stop the background scheduler"""
    scheduler.shutdown()
    logger.info("Scheduler stopped")
