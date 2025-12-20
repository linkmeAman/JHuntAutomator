import asyncio
import json
import logging
import os
import ssl
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
from threading import Thread

import httpx
import requests
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import IntegrityError

from backend.config import settings
from backend.models import Job, CrawlRun
from backend.nlp import get_nlp_scorer
from backend.crawl_engine.fetcher import Fetcher
from backend.crawl_engine.metrics import Metrics
from backend.crawl_engine.dedupe import compute_keys
from backend.crawl_engine.normalize import build_normalized, canonical_url
from backend.crawl_engine.state import load_state, update_state_failure, update_state_success, get_cursor, set_cursor
from backend.crawl_engine.types import RawJob
from backend.crawl_engine import state as state_module
from backend.crawl_engine.errors import (
    SourceBlockedError,
    SourceBadConfigError,
    SourceTransientNetworkError,
    SourceTLSCertError,
    SourceRateLimitedError,
)
from backend.database import SessionLocal
from backend.crawl_engine.query_utils import generate_queries
from backend.crawl_engine.normalize import canonical_url

logger = logging.getLogger(__name__)
DEBUG_DEDUPE = os.getenv("CRAWL_DEBUG_DEDUPE") == "1"


STOP_ON_SEEN_RATIO = settings.CRAWL_STOP_ON_SEEN_RATIO


class EngineV2:
    def __init__(self, db: Session, ignore_cooldown: bool = False):
        self.db = db
        self.ignore_cooldown = ignore_cooldown
        self.fetcher = Fetcher(
            max_concurrent_global=10,
            per_domain=2,
            min_delay_ms=settings.REQUEST_DELAY_MS_MIN,
            max_delay_ms=settings.REQUEST_DELAY_MS_MAX,
        )
        self.metrics = Metrics()
        self.nlp_scorer = get_nlp_scorer()

    async def run_sources(self, source_functions: Dict[str, callable], sources_enabled: dict):
        tasks = []
        for name, fn in source_functions.items():
            if not sources_enabled.get(name, False):
                continue
            tasks.append(self._run_source(name, fn))
        await asyncio.gather(*tasks)

    async def _run_source(self, name: str, fn: callable):
        state = load_state(self.db, name)
        if not self.ignore_cooldown and state.cooldown_until and state.cooldown_until > datetime.utcnow():
            logger.warning("Source %s in cooldown until %s", name, state.cooldown_until)
            return
        cursor_info = get_cursor(state)
        cursor_info = cursor_info or {}
        cursor_info.setdefault("http_cache", {})
        since = self._compute_since(cursor_info)
        try:
            # Existing sources are sync; run in thread to allow concurrency
            try:
                jobs_raw = await asyncio.to_thread(fn, cursor_info)
            except TypeError:
                jobs_raw = await asyncio.to_thread(fn)
            if os.getenv("CRAWL_TEST_DEBUG") == "1":
                logger.info("CRAWL_DEBUG source=%s dry_run=%s enabled=%s", name, False, True)
            parsed_jobs: List[RawJob] = []
            fetched = len(jobs_raw)
            self.metrics.source[name]["fetched_count"] = fetched
            for j in jobs_raw:
                try:
                    if hasattr(j, "model_dump"):
                        payload = j.model_dump()
                    elif hasattr(j, "dict"):
                        payload = j.dict()
                    elif isinstance(j, dict):
                        payload = j
                    else:
                        payload = {}
                    parsed_jobs.append(RawJob(**payload))
                    self.metrics.source[name]["jobs_parsed_count"] += 1
                except Exception as exc:
                    self.metrics.source[name]["errors"].append(str(exc))
            normalized_payloads = []
            for raw in parsed_jobs:
                job_key, job_hash = compute_keys(raw.dict())
                norm = build_normalized(raw, job_hash, job_key)
                self._update_last_seen(cursor_info, raw)
                if self.nlp_scorer:
                    try:
                        score = self.nlp_scorer.score(f"{norm.title} {norm.description}")
                        norm.relevance_score = score
                        self.metrics.source[name]["jobs_scored_count"] += 1
                        self.metrics.source[name]["jobs_above_threshold_count"] += 1
                        self.metrics.source[name]["matched_count"] += 1
                    except Exception as exc:
                        self.metrics.source[name]["errors"].append(str(exc))
                normalized_payloads.append(norm)
                self.metrics.source[name]["jobs_insert_attempted_count"] += 1
            self.metrics.source[name]["jobs_normalized_count"] = len(normalized_payloads)

            # upsert with optimistic insert, dedupe on IntegrityError
            updated_jobs = 0
            dedup_count = 0
            inserted_count = 0
            for norm in normalized_payloads:
                # Ensure keys/hashes are present and deterministic
                if not norm.job_key or not norm.job_hash:
                    k, h = compute_keys(norm.dict())
                    norm.job_key = k
                    norm.job_hash = h
                if DEBUG_DEDUPE:
                    logger.info(
                        "DEDUPE_DEBUG source=%s key=%s url=%s canonical=%s",
                        name,
                        norm.job_key,
                        norm.url,
                        canonical_url(norm.url),
                    )
                payload = norm.dict()
                if payload.get("source_meta") is not None:
                    payload["source_meta"] = json.dumps(payload["source_meta"])
                payload["last_seen_at"] = datetime.now(timezone.utc)
                payload["updated_at"] = datetime.now(timezone.utc)
                try:
                    new_job = Job(**payload)
                    self.db.add(new_job)
                    self.db.flush()
                    inserted_count += 1
                except IntegrityError:
                    # Already exists: update last_seen and, if fingerprint changed, fields.
                    self.db.rollback()
                    existing = self.db.query(Job).filter(Job.job_key == norm.job_key).first()
                    if existing:
                        if existing.job_fingerprint != norm.job_fingerprint:
                            existing.title = norm.title
                            existing.company = norm.company
                            existing.location = norm.location
                            existing.description = norm.description
                            existing.source_meta = json.dumps(norm.source_meta) if norm.source_meta else None
                            existing.relevance_score = norm.relevance_score
                            existing.updated_at = datetime.now(timezone.utc)
                            existing.last_seen_at = datetime.now(timezone.utc)
                            updated_jobs += 1
                            self.metrics.source[name]["jobs_updated_count"] += 1
                        else:
                            existing.last_seen_at = datetime.now(timezone.utc)
                        dedup_count += 1
                except Exception as exc:
                    self.db.rollback()
                    self.metrics.source[name]["errors"].append(str(exc))

            if inserted_count:
                self.metrics.source[name]["jobs_inserted_count"] += inserted_count
            self.metrics.source[name]["jobs_deduped_count"] += dedup_count
            total_considered = len(normalized_payloads) or 1
            seen_ratio = dedup_count / total_considered
            if seen_ratio >= STOP_ON_SEEN_RATIO:
                marker = f"stop_on_seen_ratio_triggered:{seen_ratio:.2f}"
                self.metrics.source[name]["errors"].append(marker)
                if os.getenv("CRAWL_TEST_DEBUG") == "1":
                    logger.info("CRAWL_DEBUG %s %s", name, marker)
            self.db.commit()
            self._store_cursor(state, cursor_info)
            update_state_success(self.db, state, cursor=cursor_info)
            logger.info(
                "Crawl source %s: parsed=%d normalized=%d new=%d dedup=%d updated=%d errors=%d seen_ratio=%.2f",
                name,
                len(parsed_jobs),
                len(normalized_payloads),
                inserted_count,
                dedup_count,
                updated_jobs,
                len(self.metrics.source[name]["errors"]),
                seen_ratio,
            )
        except Exception as exc:
            self.db.rollback()
            cooldown_minutes = self._classify_and_cooldown(exc, state)
            suffix = f" (cooldown {cooldown_minutes}m)" if cooldown_minutes else ""
            self.metrics.source[name]["errors"].append(f"{type(exc).__name__}: {exc}{suffix}")

    async def close(self):
        await self.fetcher.close()

    def _compute_since(self, cursor: dict) -> datetime:
        now = datetime.now(timezone.utc)
        lookback = now - timedelta(days=settings.CRAWL_LOOKBACK_DAYS)
        last_seen = None
        if cursor.get("last_max_post_date_seen"):
            try:
                last_seen = datetime.fromisoformat(cursor["last_max_post_date_seen"])
                if last_seen.tzinfo is None:
                    last_seen = last_seen.replace(tzinfo=timezone.utc)
            except Exception:
                last_seen = None
        if last_seen:
            last_seen = last_seen - timedelta(days=settings.CRAWL_LOOKBACK_BUFFER_DAYS)
            return max(lookback, last_seen)
        return lookback

    def _update_last_seen(self, cursor: dict, raw: RawJob):
        post_date = getattr(raw, "post_date", None)
        if not post_date:
            return
        try:
            if isinstance(post_date, str):
                dt = datetime.fromisoformat(post_date.replace("Z", "+00:00"))
            elif isinstance(post_date, datetime):
                dt = post_date
            else:
                return
            cur = cursor.get("last_max_post_date_seen")
            cur_dt = datetime.fromisoformat(cur) if cur else None
            if (not cur_dt) or dt > cur_dt:
                cursor["last_max_post_date_seen"] = dt.isoformat()
        except Exception:
            return

    def _store_cursor(self, state, cursor: dict):
        if not cursor:
            return
        set_cursor(state, cursor)
        self.db.add(state)
        self.db.commit()

    def _classify_and_cooldown(self, exc: Exception, state) -> int | None:
        """Determine cooldown based on error taxonomy."""
        cooldown_minutes: int | None = None
        reason = None
        if isinstance(exc, SourceBlockedError):
            reason = "blocked"
            cooldown_minutes = min(120, 30 * max(1, state.consecutive_failures + 1))
        elif isinstance(exc, SourceRateLimitedError):
            reason = "ratelimited"
            cooldown_minutes = min(120, 30 * max(1, state.consecutive_failures + 1))
        elif isinstance(exc, SourceBadConfigError):
            reason = "bad_config"
            cooldown_minutes = 120
        elif isinstance(exc, SourceTLSCertError) or isinstance(exc, requests.exceptions.SSLError):
            reason = "tls"
            cooldown_minutes = 60
            logger.warning("TLS error for source; verify CA bundle at %s", settings.CA_BUNDLE_PATH or "certifi")
        elif isinstance(exc, SourceTransientNetworkError) or isinstance(exc, httpx.RemoteProtocolError) or isinstance(exc, httpx.ReadTimeout):
            reason = "transient"
            # Only cooldown after 3 consecutive failures
            if (state.consecutive_failures or 0) + 1 >= 3:
                cooldown_minutes = min(15, 5 * max(1, state.consecutive_failures + 1))
        elif isinstance(exc, Exception):
            # Fallback: treat as transient
            if (state.consecutive_failures or 0) + 1 >= 3:
                cooldown_minutes = 10

        state.consecutive_failures = (state.consecutive_failures or 0) + 1
        if cooldown_minutes:
            state.cooldown_until = datetime.utcnow() + timedelta(minutes=cooldown_minutes)
        self.db.add(state)
        self.db.commit()
        return cooldown_minutes


def run_engine_v2(
    db: Session,
    sources_enabled: dict,
    source_functions: Dict[str, callable],
    ignore_cooldown: bool = False,
    session_maker: sessionmaker | None = None,
):
    result_holder = {}

    def worker():
        local_session = (session_maker or SessionLocal)()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        engine = EngineV2(local_session, ignore_cooldown=ignore_cooldown)
        try:
            loop.run_until_complete(engine.run_sources(source_functions, sources_enabled))
            result_holder["metrics"] = engine.metrics.to_json()
        finally:
            loop.run_until_complete(engine.close())
            loop.close()
            local_session.close()

    t = Thread(target=worker, daemon=True)
    t.start()
    t.join()
    return result_holder.get("metrics", {})
