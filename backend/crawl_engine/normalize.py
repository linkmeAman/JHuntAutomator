from __future__ import annotations

import hashlib
from urllib.parse import urlparse, parse_qsl, urlunparse

from .types import NormalizedJob, RawJob


def canonical_url(url: str) -> str:
    parsed = urlparse(url.strip())
    query_items = []
    for k, v in parse_qsl(parsed.query, keep_blank_values=True):
        if k.lower().startswith("utm_"):
            continue
        query_items.append((k, v))
    normalized_query = "&".join(f"{k}={v}" for k, v in query_items)
    normalized = parsed._replace(fragment="", query=normalized_query)
    normalized_url = urlunparse(normalized).rstrip("/")
    return normalized_url.lower()


def fingerprint(raw: RawJob) -> str:
    content = "|".join(
        [
            raw.title.strip().lower(),
            (raw.company or "").strip().lower(),
            (raw.location or "").strip().lower(),
            (raw.description or "")[:200].strip().lower(),
        ]
    )
    return hashlib.sha256(content.encode()).hexdigest()


def build_normalized(raw: RawJob, job_hash: str, job_key: str) -> NormalizedJob:
    return NormalizedJob(
        title=raw.title or "Untitled",
        company=raw.company or "Unknown",
        location=raw.location or "Remote",
        url=canonical_url(raw.url),
        description=raw.description or raw.title,
        post_date=raw.post_date,
        source=raw.source,
        source_meta=raw.source_meta,
        remote=raw.remote,
        relevance_score=0.0,
        keywords_matched=None,
        job_hash=job_hash,
        job_key=job_key,
        job_fingerprint=fingerprint(raw),
    )
