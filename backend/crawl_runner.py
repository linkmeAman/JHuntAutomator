import json
import logging
from datetime import datetime, timezone
from typing import List, Tuple
from uuid import uuid4

from sqlalchemy.orm import Session

from .config import settings
from .crawler import JobCrawler
from .http_client import SourceBlockedError
from .models import CrawlRun, Job, Settings as SettingsModel
from .nlp import get_nlp_scorer
from .notifications import NotificationService
from .schemas import CrawlResult, JobCreate
from .sources import (
    remotive,
    workingnomads,
    naukri,
    shine,
    timesjobs,
    remote_co,
    glassdoor,
    wellfound,
    yc,
    linkedin,
)

logger = logging.getLogger(__name__)


def _merge_sources(stored_sources: dict | None) -> dict:
    merged = settings.JOB_SOURCES.copy()
    if stored_sources:
        merged.update(stored_sources)
    return merged


def _normalize_greenhouse_boards(raw_boards) -> List[dict]:
    normalized: List[dict] = []
    if not raw_boards:
        return normalized

    for item in raw_boards:
        if isinstance(item, dict) and "board_url" in item:
            name = item.get("name") or item["board_url"].rstrip("/").split("/")[-1]
            normalized.append({"name": name, "board_url": item["board_url"]})
        elif isinstance(item, str):
            normalized.append(
                {
                    "name": item.replace("-", " ").title(),
                    "board_url": f"https://boards.greenhouse.io/{item}",
                }
            )
    return normalized


def _load_runtime_settings(db: Session) -> Tuple[List[str], List[str], dict, List[dict]]:
    keywords_setting = (
        db.query(SettingsModel).filter(SettingsModel.key == "keywords").first()
    )
    locations_setting = (
        db.query(SettingsModel).filter(SettingsModel.key == "locations").first()
    )
    sources_setting = (
        db.query(SettingsModel).filter(SettingsModel.key == "sources").first()
    )
    greenhouse_boards_setting = (
        db.query(SettingsModel).filter(SettingsModel.key == "greenhouse_boards").first()
    )

    keywords = (
        json.loads(keywords_setting.value)
        if keywords_setting and keywords_setting.value
        else settings.DEFAULT_KEYWORDS
    )
    locations = (
        json.loads(locations_setting.value)
        if locations_setting and locations_setting.value
        else settings.DEFAULT_LOCATIONS
    )
    sources = (
        json.loads(sources_setting.value)
        if sources_setting and sources_setting.value
        else settings.JOB_SOURCES
    )
    greenhouse_boards = (
        json.loads(greenhouse_boards_setting.value)
        if greenhouse_boards_setting and greenhouse_boards_setting.value
        else settings.GREENHOUSE_BOARDS
    )
    greenhouse_boards = _normalize_greenhouse_boards(greenhouse_boards) or settings.GREENHOUSE_BOARDS

    return keywords, locations, _merge_sources(sources), greenhouse_boards


def execute_crawl(
    db: Session,
    *,
    send_notifications: bool = False,
    dry_run: bool = False,
    override_sources: dict | None = None,
    max_pages: int | None = None,
    min_store_score: float | None = None,
) -> CrawlResult:
    """Run the crawler pipeline once."""
    keywords, locations, sources, greenhouse_boards = _load_runtime_settings(db)
    if override_sources:
        merged = sources.copy()
        merged.update(override_sources)
        sources = merged
    nlp_scorer = get_nlp_scorer()

    run_id = str(uuid4())
    run_started_at = datetime.now(timezone.utc)

    crawler = JobCrawler(
        keywords,
        locations,
        max_jobs=settings.MAX_JOBS_PER_SOURCE,
        nlp_scorer=nlp_scorer,
        greenhouse_boards=greenhouse_boards,
    )

    attempted_sources: List[str] = []
    succeeded_sources: List[str] = []
    failed_sources: List[dict] = []
    source_metrics: List[dict] = []
    jobs_found: List[JobCreate] = []

    source_functions = {
        "remoteok": lambda: crawler.crawl_remoteok(),
        "weworkremotely": lambda: crawler.crawl_weworkremotely_rss(),
        "indeed": lambda: crawler.crawl_indeed(),
        "greenhouse": lambda: crawler.crawl_greenhouse_boards(),
        "remotive": lambda: remotive.fetch_jobs(settings),
        "workingnomads": lambda: workingnomads.fetch_jobs(settings),
        "remote_co": lambda: remote_co.fetch_jobs(settings),
        "naukri": lambda: naukri.fetch_jobs(settings),
        "shine": lambda: shine.fetch_jobs(settings),
        "timesjobs": lambda: timesjobs.fetch_jobs(settings),
        "glassdoor": lambda: glassdoor.fetch_jobs(settings),
        "wellfound": lambda: wellfound.fetch_jobs(settings),
        "yc": lambda: yc.fetch_jobs(settings),
        "linkedin": lambda: linkedin.fetch_jobs(settings),
    }

    for source_name, crawl_fn in source_functions.items():
        if not sources.get(source_name, False):
            continue
        attempted_sources.append(source_name)

        metrics = {
            "source": source_name,
            "requested_pages": max_pages or settings.MAX_PAGES_PER_SOURCE,
            "pages_fetched": 0,
            "http_status_counts": {},
            "jobs_parsed_count": 0,
            "jobs_after_normalization_count": 0,
            "jobs_scored_count": 0,
            "jobs_above_threshold_count": 0,
            "jobs_insert_attempted_count": 0,
            "jobs_inserted_count": 0,
            "jobs_deduped_count": 0,
            "errors": [],
        }
        try:
            if source_name == "indeed":
                logger.warning(
                    "Indeed scraping is brittle/ToS-sensitive; enable only for personal use."
                )
            jobs = crawl_fn()
            if source_name in {"remotive", "workingnomads", "remote_co", "naukri", "shine", "timesjobs", "linkedin"}:
                # Normalize dicts into JobCreate-like objects after scoring
                scored_jobs: List[JobCreate] = []
                for job_dict in jobs:
                    metrics["jobs_parsed_count"] += 1
                    score, keywords_matched = crawler.calculate_relevance_score(job_dict)
                    metrics["jobs_scored_count"] += 1
                    if score >= (min_store_score if min_store_score is not None else settings.MIN_SCORE_TO_STORE):
                        metrics["jobs_above_threshold_count"] += 1
                    job_hash = Job.generate_hash(
                        job_dict.get("title", ""),
                        job_dict.get("company", ""),
                        job_dict.get("url", ""),
                        job_dict.get("source", ""),
                        job_dict.get("post_date"),
                        job_dict.get("location"),
                    )
                    job_key = Job.generate_key(
                        job_dict.get("title", ""),
                        job_dict.get("company", ""),
                        job_dict.get("url", ""),
                        job_dict.get("source", ""),
                        job_dict.get("post_date"),
                        job_dict.get("location"),
                    )
                    job_payload = {
                        **job_dict,
                        "job_hash": job_hash,
                        "job_key": job_key,
                        "relevance_score": score,
                        "keywords_matched": keywords_matched,
                    }
                    scored_jobs.append(JobCreate(**job_payload))
                jobs_found.extend(scored_jobs)
            else:
                jobs_found.extend(jobs)
            succeeded_sources.append(source_name)
        except SourceBlockedError as exc:
            failed_sources.append({"source": source_name, "error": str(exc)})
            logger.warning("Source %s blocked: %s", source_name, exc)
            metrics["errors"].append(str(exc))
        except Exception as exc:
            failed_sources.append({"source": source_name, "error": str(exc)})
            logger.error("Source %s failed: %s", source_name, exc)
            metrics["errors"].append(str(exc))
        source_metrics.append(metrics)

    jobs_found.sort(key=lambda x: x.relevance_score, reverse=True)

    new_jobs: List[Job] = []
    run_entry = CrawlRun(
        run_id=run_id,
        started_at=run_started_at,
        sources_attempted=json.dumps(attempted_sources),
        sources_succeeded=json.dumps([]),
        sources_failed=json.dumps([]),
        source_metrics=json.dumps(source_metrics),
        fetched_count=0,
        inserted_new_count=0,
    )
    db.add(run_entry)
    db.commit()

    try:
        jobs_to_save: List[Job] = []
        for job_data in jobs_found:
            existing_job = db.query(Job).filter(Job.job_key == job_data.job_key).first()
            if existing_job:
                metrics_entry = next((m for m in source_metrics if m["source"] == job_data.source), None)
                if metrics_entry:
                    metrics_entry["jobs_deduped_count"] += 1
                continue
            payload = job_data.dict()
            if payload.get("source_meta") is not None:
                payload["source_meta"] = json.dumps(payload["source_meta"])
            new_job = Job(**payload)
            jobs_to_save.append(new_job)
            new_jobs.append(new_job)
            metrics_entry = next((m for m in source_metrics if m["source"] == job_data.source), None)
            if metrics_entry:
                metrics_entry["jobs_insert_attempted_count"] += 1

        if jobs_to_save and not dry_run:
            db.bulk_save_objects(jobs_to_save)
        if not dry_run:
            db.commit()
    except Exception as exc:
        db.rollback()
        failed_sources.append({"source": "pipeline", "error": str(exc)})
        logger.error("Crawl pipeline failed: %s", exc)
    finally:
        finished_at = datetime.now(timezone.utc)
        run_entry.finished_at = finished_at
        run_entry.duration_ms = int((finished_at - run_started_at).total_seconds() * 1000)
        run_entry.fetched_count = len(jobs_found)
        run_entry.inserted_new_count = len(new_jobs)
        run_entry.sources_attempted = json.dumps(attempted_sources)
        run_entry.sources_succeeded = json.dumps(succeeded_sources)
        run_entry.sources_failed = json.dumps(failed_sources)
        run_entry.source_metrics = json.dumps(source_metrics)
        if failed_sources:
            run_entry.errors_summary = "; ".join(
                f"{item.get('source')}: {item.get('error')}" for item in failed_sources
            )
        db.add(run_entry)
        if not dry_run:
            db.commit()
        else:
            db.rollback()

    if send_notifications and settings.ENABLE_NOTIFICATIONS:
        notifier = NotificationService()
        if new_jobs:
            notifier.send_daily_digest(new_jobs)
        notifier.send_run_alerts(run_entry)

    logger.info(
        "Crawl complete: %s jobs discovered, %s new jobs stored",
        len(jobs_found),
        len(new_jobs),
    )

    return CrawlResult(
        status="success",
        jobs_found=len(jobs_found),
        jobs_added=len(new_jobs),
        message=f"Found {len(jobs_found)} jobs, added {len(new_jobs)} new jobs",
        run_id=run_id,
    )
