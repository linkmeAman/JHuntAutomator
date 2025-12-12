from pydantic import BaseModel, Field
from typing import Optional, List
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
    crawl_hour: int
    crawl_minute: int

class CrawlResult(BaseModel):
    status: str
    jobs_found: int
    jobs_added: int
    message: str


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
