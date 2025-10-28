from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class JobBase(BaseModel):
    title: str
    company: str
    location: str
    description: str
    requirements: Optional[str] = None
    url: str
    source: str
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
    crawl_hour: int
    crawl_minute: int

class CrawlResult(BaseModel):
    status: str
    jobs_found: int
    jobs_added: int
    message: str
