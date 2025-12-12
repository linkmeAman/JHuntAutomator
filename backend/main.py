from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import List, Optional
import json
import logging

from .database import get_db, init_db
from .models import CrawlRun, Job, Settings as SettingsModel
from .schemas import JobResponse, JobUpdate, SettingsSchema, CrawlResult, CrawlRunSchema
from .config import settings
from .scheduler import start_scheduler
from .crawl_runner import execute_crawl

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
        start_scheduler_if_configured(app)
    finally:
        db.close()


def start_scheduler_if_configured(app):
    """Start scheduler only when configured for server mode."""
    mode = settings.CRAWL_MODE.lower()
    if mode == "server":
        start_scheduler(app)
        logger.info("Scheduler started (mode=server)")
    else:
        logger.info("Scheduler not started (mode=%s)", mode)


def _deserialize_json_field(value: str | None, default):
    try:
        return json.loads(value) if value else default
    except Exception:
        return default


def _serialize_run(run: CrawlRun) -> CrawlRunSchema:
    return CrawlRunSchema(
        run_id=run.run_id,
        started_at=run.started_at,
        finished_at=run.finished_at,
        duration_ms=run.duration_ms,
        sources_attempted=_deserialize_json_field(run.sources_attempted, []),
        sources_succeeded=_deserialize_json_field(run.sources_succeeded, []),
        sources_failed=_deserialize_json_field(run.sources_failed, []),
        fetched_count=run.fetched_count,
        inserted_new_count=run.inserted_new_count,
        errors_summary=run.errors_summary,
    )

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
    if sources_setting and sources_setting.value:
        stored_sources = json.loads(sources_setting.value)
        merged_sources = settings.JOB_SOURCES.copy()
        merged_sources.update(stored_sources)
        sources_setting.value = json.dumps(merged_sources)
    else:
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

    greenhouse_setting = db.query(SettingsModel).filter(SettingsModel.key == "greenhouse_boards").first()
    if greenhouse_setting and greenhouse_setting.value:
        try:
            stored_boards = json.loads(greenhouse_setting.value)
        except Exception:
            stored_boards = settings.GREENHOUSE_BOARDS
        greenhouse_setting.value = json.dumps(stored_boards or settings.GREENHOUSE_BOARDS)
    else:
        greenhouse_setting = SettingsModel(
            key="greenhouse_boards",
            value=json.dumps(settings.GREENHOUSE_BOARDS)
        )
        db.add(greenhouse_setting)
    
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
        return execute_crawl(db)
    except Exception as e:
        logger.error(f"Error during crawl: {e}")
        raise HTTPException(status_code=500, detail=f"Crawl failed: {str(e)}")


@app.post("/api/crawl/rescan", response_model=CrawlResult)
async def rescan_jobs_alias(db: Session = Depends(get_db)):
    """Alias endpoint for manual crawl"""
    return await rescan_jobs(db)

@app.get("/health")
async def healthcheck(db: Session = Depends(get_db)):
    """Healthcheck for ops dashboards."""
    db_ok = True
    db_error = None
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - defensive
        db_ok = False
        db_error = str(exc)

    last_run = (
        db.query(CrawlRun).order_by(CrawlRun.started_at.desc()).limit(1).first()
    )

    return {
        "status": "ok" if db_ok else "degraded",
        "scheduler_mode": settings.CRAWL_MODE,
        "db_ok": db_ok,
        "db_error": db_error,
        "last_run": _serialize_run(last_run) if last_run else None,
    }

@app.get("/api/settings", response_model=SettingsSchema)
async def get_settings(db: Session = Depends(get_db)):
    """Get current settings"""
    keywords_setting = db.query(SettingsModel).filter(SettingsModel.key == "keywords").first()
    locations_setting = db.query(SettingsModel).filter(SettingsModel.key == "locations").first()
    sources_setting = db.query(SettingsModel).filter(SettingsModel.key == "sources").first()
    schedule_setting = db.query(SettingsModel).filter(SettingsModel.key == "schedule").first()
    greenhouse_setting = db.query(SettingsModel).filter(SettingsModel.key == "greenhouse_boards").first()
    
    keywords = json.loads(keywords_setting.value) if keywords_setting else settings.DEFAULT_KEYWORDS
    locations = json.loads(locations_setting.value) if locations_setting else settings.DEFAULT_LOCATIONS
    sources = json.loads(sources_setting.value) if sources_setting else settings.JOB_SOURCES
    if sources:
        merged_sources = settings.JOB_SOURCES.copy()
        merged_sources.update(sources)
        sources = merged_sources
    schedule = json.loads(schedule_setting.value) if schedule_setting else {"hour": settings.CRAWL_SCHEDULE_HOUR, "minute": settings.CRAWL_SCHEDULE_MINUTE}
    greenhouse_boards = json.loads(greenhouse_setting.value) if greenhouse_setting else settings.GREENHOUSE_BOARDS
    
    return SettingsSchema(
        keywords=keywords,
        locations=locations,
        sources=sources,
        greenhouse_boards=greenhouse_boards,
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
    
    greenhouse_setting = db.query(SettingsModel).filter(SettingsModel.key == "greenhouse_boards").first()
    boards_payload = []
    for board in settings_data.greenhouse_boards:
        if hasattr(board, "model_dump"):
            boards_payload.append(board.model_dump())
        else:
            boards_payload.append(board)
    if greenhouse_setting:
        greenhouse_setting.value = json.dumps(boards_payload)
    else:
        db.add(SettingsModel(key="greenhouse_boards", value=json.dumps(boards_payload)))
    
    schedule_setting = db.query(SettingsModel).filter(SettingsModel.key == "schedule").first()
    schedule_data = {"hour": settings_data.crawl_hour, "minute": settings_data.crawl_minute}
    if schedule_setting:
        schedule_setting.value = json.dumps(schedule_data)
    else:
        db.add(SettingsModel(key="schedule", value=json.dumps(schedule_data)))
    
    db.commit()
    
    return settings_data


@app.get("/api/runs", response_model=List[CrawlRunSchema])
async def list_runs(
    limit: int = Query(10, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    """List recent crawl runs"""
    runs = (
        db.query(CrawlRun)
        .order_by(CrawlRun.started_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_serialize_run(run) for run in runs]


@app.get("/api/runs/{run_id}", response_model=CrawlRunSchema)
async def get_run(run_id: str, db: Session = Depends(get_db)):
    """Get details for a specific crawl run"""
    run = db.query(CrawlRun).filter(CrawlRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return _serialize_run(run)

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
