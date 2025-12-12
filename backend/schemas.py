from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from .config import settings


class GreenhouseBoard(BaseModel):
    name: str
    board_url: str

class JobBase(BaseModel):
    title: str
    company: str
    location: str
    description: str
    requirements: Optional[str] = None
    url: str
    source: str
    source_detail: Optional[str] = None
    post_date: Optional[str] = None
    remote: bool = False
    source_meta: Optional[Dict[str, Any]] = None

class JobCreate(JobBase):
    job_hash: str
    relevance_score: float = 0.0
    keywords_matched: Optional[str] = None

class JobUpdate(BaseModel):
    applied: Optional[bool] = None
    notes: Optional[str] = None

class JobResponse(JobBase):
    id: int
    job_hash: str
    relevance_score: float
    keywords_matched: Optional[str] = None
    source_detail: Optional[str] = None
    source_meta: Optional[Dict[str, Any]] = None
    applied: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class SettingsSchema(BaseModel):
    keywords: List[str]
    locations: List[str]
    sources: dict
    greenhouse_boards: List[GreenhouseBoard] = Field(default_factory=lambda: settings.GREENHOUSE_BOARDS)
    india_mode: bool = Field(default_factory=lambda: settings.INDIA_MODE)
    linkedin_mode: str = Field(default_factory=lambda: settings.LINKEDIN_MODE)
    linkedin_email: Dict[str, Any] = Field(default_factory=lambda: settings.LINKEDIN_EMAIL)
    linkedin_crawl: Dict[str, Any] = Field(default_factory=lambda: settings.LINKEDIN_CRAWL)
    crawl_hour: int
    crawl_minute: int

class CrawlResult(BaseModel):
    status: str
    jobs_found: int
    jobs_added: int
    message: str
    run_id: Optional[str] = None


class SourceFailure(BaseModel):
    source: str
    error: str


class CrawlRunSchema(BaseModel):
    run_id: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    sources_attempted: List[str] = Field(default_factory=list)
    sources_succeeded: List[str] = Field(default_factory=list)
    sources_failed: List[SourceFailure] = Field(default_factory=list)
    fetched_count: int
    inserted_new_count: int
    errors_summary: Optional[str] = None

    class Config:
        from_attributes = True
