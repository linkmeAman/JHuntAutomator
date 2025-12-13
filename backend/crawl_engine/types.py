from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, HttpUrl, Field


@dataclass
class RequestSpec:
    url: str
    method: str = "GET"
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, Any]] = None
    body: Optional[Any] = None
    domain: Optional[str] = None


class RawJob(BaseModel):
    title: str
    company: str | None = None
    location: str | None = None
    url: str
    description: str | None = None
    post_date: str | None = None
    source: str
    source_meta: Dict[str, Any] | None = None
    remote: bool = False

    class Config:
        extra = "ignore"


class NormalizedJob(BaseModel):
    title: str
    company: str
    location: str
    url: HttpUrl
    description: str
    post_date: str | None = None
    source: str
    source_meta: Dict[str, Any] | None = None
    remote: bool = False
    relevance_score: float = 0.0
    keywords_matched: Optional[str] = None
    job_hash: str
    job_key: str
    job_fingerprint: str
