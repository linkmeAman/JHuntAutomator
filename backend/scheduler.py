from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
import json
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def scheduled_crawl(app):
    """Function to run scheduled job crawl"""
    logger.info("Starting scheduled job crawl...")
    
    from .database import SessionLocal
    from .models import Settings as SettingsModel, Job
    from .crawler import JobCrawler
    from .config import settings
    
    db = SessionLocal()
    try:
        keywords_setting = db.query(SettingsModel).filter(SettingsModel.key == "keywords").first()
        locations_setting = db.query(SettingsModel).filter(SettingsModel.key == "locations").first()
        sources_setting = db.query(SettingsModel).filter(SettingsModel.key == "sources").first()
        
        keywords = json.loads(keywords_setting.value) if keywords_setting else settings.DEFAULT_KEYWORDS
        locations = json.loads(locations_setting.value) if locations_setting else settings.DEFAULT_LOCATIONS
        sources = json.loads(sources_setting.value) if sources_setting else settings.JOB_SOURCES
        
        crawler = JobCrawler(keywords, locations, max_jobs=settings.MAX_JOBS_PER_SOURCE)
        jobs_found = crawler.crawl_all_sources(sources)
        
        jobs_added = 0
        for job_data in jobs_found:
            existing_job = db.query(Job).filter(Job.job_hash == job_data.job_hash).first()
            if not existing_job:
                new_job = Job(**job_data.dict())
                db.add(new_job)
                jobs_added += 1
        
        db.commit()
        logger.info(f"Scheduled crawl complete: {len(jobs_found)} found, {jobs_added} new jobs added")
        
    except Exception as e:
        logger.error(f"Error during scheduled crawl: {e}")
        db.rollback()
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
