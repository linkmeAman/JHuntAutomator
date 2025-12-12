from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime
from sqlalchemy.sql import func
from .database import Base
import hashlib
from urllib.parse import urlparse, parse_qsl, urlunparse
from uuid import uuid4

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_hash = Column(String, unique=True, index=True)
    job_key = Column(String, unique=True, index=True)
    title = Column(String, index=True)
    company = Column(String, index=True)
    location = Column(String)
    description = Column(Text)
    requirements = Column(Text, nullable=True)
    url = Column(String)
    source = Column(String)
    source_detail = Column(String, nullable=True)
    post_date = Column(String, nullable=True)
    remote = Column(Boolean, default=False)
    source_meta = Column(Text, nullable=True)
    relevance_score = Column(Float, default=0.0)
    keywords_matched = Column(String, nullable=True)
    applied = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    @staticmethod
    def _normalize_url(url: str) -> str:
        if not url:
            return ""
        parsed = urlparse(url.strip())
        # drop common tracking params, keep id-like params
        query_items = []
        for k, v in parse_qsl(parsed.query, keep_blank_values=True):
            if k.lower().startswith("utm_"):
                continue
            query_items.append((k, v))
        normalized_query = "&".join(f"{k}={v}" for k, v in query_items)
        normalized = parsed._replace(fragment="", query=normalized_query)
        normalized_url = urlunparse(normalized).rstrip("/")
        return normalized_url.lower()

    @staticmethod
    def generate_key(title: str, company: str, url: str, source: str | None = None, post_date: str | None = None, location: str | None = None) -> str:
        normalized_url = Job._normalize_url(url)
        if normalized_url:
            content = f"{source or ''}|{normalized_url}".lower()
            return hashlib.sha256(content.encode()).hexdigest()
        # fallback when URL missing
        parts = [
            (source or "").strip().lower(),
            title.strip().lower(),
            company.strip().lower(),
            (location or "").strip().lower(),
            (post_date or "").strip().lower(),
        ]
        content = "|".join(parts)
        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    def generate_hash(title: str, company: str, url: str, source: str | None = None, post_date: str | None = None, location: str | None = None) -> str:
        # kept for backward compatibility, now delegates to generate_key
        return Job.generate_key(title, company, url, source, post_date, location)


class Settings(Base):
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(Text)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class CrawlRun(Base):
    __tablename__ = "crawl_runs"

    run_id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    sources_attempted = Column(Text, nullable=True)
    sources_succeeded = Column(Text, nullable=True)
    sources_failed = Column(Text, nullable=True)
    source_metrics = Column(Text, nullable=True)
    fetched_count = Column(Integer, default=0)
    inserted_new_count = Column(Integer, default=0)
    errors_summary = Column(Text, nullable=True)
