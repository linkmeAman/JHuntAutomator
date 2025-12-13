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
from .api_debug import router as debug_router
from backend.crawl_engine.state import SourceState, get_cursor

# Configure logging to both console and file for crawl diagnostics
log_dir = "logs"
log_file = f"{log_dir}/app.log"
try:
    import os
    os.makedirs(log_dir, exist_ok=True)
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_file, encoding="utf-8")
            ],
        )
except Exception:
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
app.include_router(debug_router)

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


def _coerce_source_meta(job: Job):
    if job and isinstance(job.source_meta, str):
        try:
            job.source_meta = json.loads(job.source_meta)
        except Exception:
            job.source_meta = None
    return job

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

@app.get("/api/sources/state")
async def get_sources_state(db: Session = Depends(get_db)):
    states = db.query(SourceState).all()
    latest_run = (
        db.query(CrawlRun)
        .order_by(CrawlRun.started_at.desc())
        .first()
    )
    metrics = {}
    if latest_run and latest_run.source_metrics:
        try:
            metrics = json.loads(latest_run.source_metrics)
        except Exception:
            metrics = {}
    result = []
    for state in states:
        cursor = get_cursor(state)
        result.append(
            {
                "source_id": state.source_id,
                "last_success_at": state.last_success_at,
                "cooldown_until": state.cooldown_until,
                "consecutive_failures": state.consecutive_failures,
                "last_max_post_date_seen": cursor.get("last_max_post_date_seen"),
                "http_cache": cursor.get("http_cache"),
                "cursor": cursor,
                "last_metrics": metrics.get(state.source_id, {}),
            }
        )
    return result

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

    india_setting = db.query(SettingsModel).filter(SettingsModel.key == "india_mode").first()
    if india_setting:
        india_setting.value = json.dumps(settings.INDIA_MODE)
    else:
        india_setting = SettingsModel(key="india_mode", value=json.dumps(settings.INDIA_MODE))
        db.add(india_setting)

    linkedin_mode_setting = db.query(SettingsModel).filter(SettingsModel.key == "linkedin_mode").first()
    if linkedin_mode_setting and linkedin_mode_setting.value:
        linkedin_mode_setting.value = linkedin_mode_setting.value
    else:
        db.add(SettingsModel(key="linkedin_mode", value=json.dumps(settings.LINKEDIN_MODE)))

    linkedin_email_setting = db.query(SettingsModel).filter(SettingsModel.key == "linkedin_email").first()
    if linkedin_email_setting and linkedin_email_setting.value:
        linkedin_email_setting.value = linkedin_email_setting.value
    else:
        db.add(SettingsModel(key="linkedin_email", value=json.dumps(settings.LINKEDIN_EMAIL)))

    linkedin_crawl_setting = db.query(SettingsModel).filter(SettingsModel.key == "linkedin_crawl").first()
    if linkedin_crawl_setting and linkedin_crawl_setting.value:
        linkedin_crawl_setting.value = linkedin_crawl_setting.value
    else:
        db.add(SettingsModel(key="linkedin_crawl", value=json.dumps(settings.LINKEDIN_CRAWL)))
    
    db.commit()

@app.get("/")
async def root():
    return {"message": "IT Job Search API", "version": "1.0.0"}

@app.get("/api/jobs", response_model=List[JobResponse])
async def get_jobs(
    q: Optional[str] = Query(None, description="Search query"),
    location: Optional[str] = Query(None, description="Filter by location"),
    applied: Optional[bool] = Query(None, description="Filter by applied status"),
    source: Optional[List[str]] = Query(None, description="Filter by source (repeat or comma-separated)"),
    remote: Optional[bool] = Query(None, description="Filter remote roles"),
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

    if source:
        sources_flat = []
        for s in source:
            sources_flat.extend([part.strip() for part in s.split(",") if part.strip()])
        if sources_flat:
            query = query.filter(Job.source.in_(sources_flat))

    if remote is not None:
        query = query.filter(Job.remote == remote)
    
    jobs = query.order_by(Job.relevance_score.desc(), Job.created_at.desc()).offset(offset).limit(limit).all()
    return [_coerce_source_meta(job) for job in jobs]

@app.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: int, db: Session = Depends(get_db)):
    """Get a specific job by ID"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _coerce_source_meta(job)

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
    return _coerce_source_meta(job)

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
    india_setting = db.query(SettingsModel).filter(SettingsModel.key == "india_mode").first()
    linkedin_mode_setting = db.query(SettingsModel).filter(SettingsModel.key == "linkedin_mode").first()
    linkedin_email_setting = db.query(SettingsModel).filter(SettingsModel.key == "linkedin_email").first()
    linkedin_crawl_setting = db.query(SettingsModel).filter(SettingsModel.key == "linkedin_crawl").first()
    
    keywords = json.loads(keywords_setting.value) if keywords_setting else settings.DEFAULT_KEYWORDS
    locations = json.loads(locations_setting.value) if locations_setting else settings.DEFAULT_LOCATIONS
    sources = json.loads(sources_setting.value) if sources_setting else settings.JOB_SOURCES
    if sources:
        merged_sources = settings.JOB_SOURCES.copy()
        merged_sources.update(sources)
        sources = merged_sources
    schedule = json.loads(schedule_setting.value) if schedule_setting else {"hour": settings.CRAWL_SCHEDULE_HOUR, "minute": settings.CRAWL_SCHEDULE_MINUTE}
    greenhouse_boards = json.loads(greenhouse_setting.value) if greenhouse_setting else settings.GREENHOUSE_BOARDS
    india_mode = json.loads(india_setting.value) if india_setting else settings.INDIA_MODE
    linkedin_mode = json.loads(linkedin_mode_setting.value) if linkedin_mode_setting else settings.LINKEDIN_MODE
    linkedin_email = json.loads(linkedin_email_setting.value) if linkedin_email_setting else settings.LINKEDIN_EMAIL
    linkedin_crawl = json.loads(linkedin_crawl_setting.value) if linkedin_crawl_setting else settings.LINKEDIN_CRAWL
    
    return SettingsSchema(
        keywords=keywords,
        locations=locations,
        sources=sources,
        greenhouse_boards=greenhouse_boards,
        india_mode=india_mode,
        linkedin_mode=linkedin_mode,
        linkedin_email=linkedin_email,
        linkedin_crawl=linkedin_crawl,
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

    india_setting = db.query(SettingsModel).filter(SettingsModel.key == "india_mode").first()
    if india_setting:
        india_setting.value = json.dumps(settings_data.india_mode)
    else:
        db.add(SettingsModel(key="india_mode", value=json.dumps(settings_data.india_mode)))

    linkedin_mode_setting = db.query(SettingsModel).filter(SettingsModel.key == "linkedin_mode").first()
    if linkedin_mode_setting:
        linkedin_mode_setting.value = json.dumps(settings_data.linkedin_mode)
    else:
        db.add(SettingsModel(key="linkedin_mode", value=json.dumps(settings_data.linkedin_mode)))

    linkedin_email_setting = db.query(SettingsModel).filter(SettingsModel.key == "linkedin_email").first()
    if linkedin_email_setting:
        linkedin_email_setting.value = json.dumps(settings_data.linkedin_email)
    else:
        db.add(SettingsModel(key="linkedin_email", value=json.dumps(settings_data.linkedin_email)))

    linkedin_crawl_setting = db.query(SettingsModel).filter(SettingsModel.key == "linkedin_crawl").first()
    if linkedin_crawl_setting:
        linkedin_crawl_setting.value = json.dumps(settings_data.linkedin_crawl)
    else:
        db.add(SettingsModel(key="linkedin_crawl", value=json.dumps(settings_data.linkedin_crawl)))
    
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
