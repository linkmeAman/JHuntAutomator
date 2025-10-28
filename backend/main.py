from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import json
import logging

from .database import get_db, init_db
from .models import Job, Settings as SettingsModel
from .schemas import JobResponse, JobUpdate, SettingsSchema, CrawlResult
from .crawler import JobCrawler
from .config import settings
from .scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="IT Job Search System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    init_db()
    logger.info("Database initialized")
    
    db = next(get_db())
    try:
        init_default_settings(db)
        start_scheduler(app)
        logger.info("Scheduler started")
    finally:
        db.close()

def init_default_settings(db: Session):
    """Initialize default settings if they don't exist"""
    keywords_setting = db.query(SettingsModel).filter(SettingsModel.key == "keywords").first()
    if not keywords_setting:
        keywords_setting = SettingsModel(
            key="keywords",
            value=json.dumps(settings.DEFAULT_KEYWORDS)
        )
        db.add(keywords_setting)
    
    locations_setting = db.query(SettingsModel).filter(SettingsModel.key == "locations").first()
    if not locations_setting:
        locations_setting = SettingsModel(
            key="locations",
            value=json.dumps(settings.DEFAULT_LOCATIONS)
        )
        db.add(locations_setting)
    
    sources_setting = db.query(SettingsModel).filter(SettingsModel.key == "sources").first()
    if not sources_setting:
        sources_setting = SettingsModel(
            key="sources",
            value=json.dumps(settings.JOB_SOURCES)
        )
        db.add(sources_setting)
    
    schedule_setting = db.query(SettingsModel).filter(SettingsModel.key == "schedule").first()
    if not schedule_setting:
        schedule_setting = SettingsModel(
            key="schedule",
            value=json.dumps({"hour": settings.CRAWL_SCHEDULE_HOUR, "minute": settings.CRAWL_SCHEDULE_MINUTE})
        )
        db.add(schedule_setting)
    
    db.commit()

@app.get("/")
async def root():
    return {"message": "IT Job Search API", "version": "1.0.0"}

@app.get("/api/jobs", response_model=List[JobResponse])
async def get_jobs(
    q: Optional[str] = Query(None, description="Search query"),
    location: Optional[str] = Query(None, description="Filter by location"),
    applied: Optional[bool] = Query(None, description="Filter by applied status"),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """Get all jobs with optional filtering"""
    query = db.query(Job)
    
    if q:
        query = query.filter(
            (Job.title.ilike(f"%{q}%")) | 
            (Job.company.ilike(f"%{q}%")) |
            (Job.description.ilike(f"%{q}%"))
        )
    
    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))
    
    if applied is not None:
        query = query.filter(Job.applied == applied)
    
    jobs = query.order_by(Job.relevance_score.desc(), Job.created_at.desc()).offset(offset).limit(limit).all()
    return jobs

@app.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: int, db: Session = Depends(get_db)):
    """Get a specific job by ID"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.patch("/api/jobs/{job_id}", response_model=JobResponse)
async def update_job(job_id: int, job_update: JobUpdate, db: Session = Depends(get_db)):
    """Update job (mark as applied, add notes)"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job_update.applied is not None:
        job.applied = job_update.applied
    if job_update.notes is not None:
        job.notes = job_update.notes
    
    db.commit()
    db.refresh(job)
    return job

@app.post("/api/rescan", response_model=CrawlResult)
async def rescan_jobs(db: Session = Depends(get_db)):
    """Manually trigger job crawling"""
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
        
        logger.info(f"Crawl complete: {len(jobs_found)} found, {jobs_added} new jobs added")
        
        return CrawlResult(
            status="success",
            jobs_found=len(jobs_found),
            jobs_added=jobs_added,
            message=f"Found {len(jobs_found)} jobs, added {jobs_added} new jobs"
        )
    
    except Exception as e:
        logger.error(f"Error during crawl: {e}")
        raise HTTPException(status_code=500, detail=f"Crawl failed: {str(e)}")

@app.get("/api/settings", response_model=SettingsSchema)
async def get_settings(db: Session = Depends(get_db)):
    """Get current settings"""
    keywords_setting = db.query(SettingsModel).filter(SettingsModel.key == "keywords").first()
    locations_setting = db.query(SettingsModel).filter(SettingsModel.key == "locations").first()
    sources_setting = db.query(SettingsModel).filter(SettingsModel.key == "sources").first()
    schedule_setting = db.query(SettingsModel).filter(SettingsModel.key == "schedule").first()
    
    keywords = json.loads(keywords_setting.value) if keywords_setting else settings.DEFAULT_KEYWORDS
    locations = json.loads(locations_setting.value) if locations_setting else settings.DEFAULT_LOCATIONS
    sources = json.loads(sources_setting.value) if sources_setting else settings.JOB_SOURCES
    schedule = json.loads(schedule_setting.value) if schedule_setting else {"hour": settings.CRAWL_SCHEDULE_HOUR, "minute": settings.CRAWL_SCHEDULE_MINUTE}
    
    return SettingsSchema(
        keywords=keywords,
        locations=locations,
        sources=sources,
        crawl_hour=schedule.get("hour", 7),
        crawl_minute=schedule.get("minute", 0)
    )

@app.put("/api/settings", response_model=SettingsSchema)
async def update_settings(settings_data: SettingsSchema, db: Session = Depends(get_db)):
    """Update settings"""
    keywords_setting = db.query(SettingsModel).filter(SettingsModel.key == "keywords").first()
    if keywords_setting:
        keywords_setting.value = json.dumps(settings_data.keywords)
    else:
        db.add(SettingsModel(key="keywords", value=json.dumps(settings_data.keywords)))
    
    locations_setting = db.query(SettingsModel).filter(SettingsModel.key == "locations").first()
    if locations_setting:
        locations_setting.value = json.dumps(settings_data.locations)
    else:
        db.add(SettingsModel(key="locations", value=json.dumps(settings_data.locations)))
    
    sources_setting = db.query(SettingsModel).filter(SettingsModel.key == "sources").first()
    if sources_setting:
        sources_setting.value = json.dumps(settings_data.sources)
    else:
        db.add(SettingsModel(key="sources", value=json.dumps(settings_data.sources)))
    
    schedule_setting = db.query(SettingsModel).filter(SettingsModel.key == "schedule").first()
    schedule_data = {"hour": settings_data.crawl_hour, "minute": settings_data.crawl_minute}
    if schedule_setting:
        schedule_setting.value = json.dumps(schedule_data)
    else:
        db.add(SettingsModel(key="schedule", value=json.dumps(schedule_data)))
    
    db.commit()
    
    return settings_data

@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get job statistics"""
    total_jobs = db.query(Job).count()
    applied_jobs = db.query(Job).filter(Job.applied == True).count()
    pending_jobs = total_jobs - applied_jobs
    
    sources = db.query(Job.source, func.count(Job.id)).group_by(Job.source).all()
    source_stats = {source: count for source, count in sources}
    
    return {
        "total_jobs": total_jobs,
        "applied_jobs": applied_jobs,
        "pending_jobs": pending_jobs,
        "sources": source_stats
    }
