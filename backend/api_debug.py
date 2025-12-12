from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .crawl_runner import execute_crawl
from .database import get_db

router = APIRouter()


@router.post("/api/crawl/debug-run")
async def debug_run(
    payload: dict,
    db: Session = Depends(get_db),
):
    sources = payload.get("sources")
    max_pages = payload.get("max_pages")
    dry_run = payload.get("dry_run", True)
    if sources and not isinstance(sources, dict):
        sources_dict = {name: True for name in sources}
    else:
        sources_dict = sources
    result = execute_crawl(
        db,
        send_notifications=False,
        dry_run=dry_run,
        override_sources=sources_dict,
        max_pages=max_pages,
    )
    return result
