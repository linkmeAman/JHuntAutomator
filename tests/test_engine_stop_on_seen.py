import asyncio
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.crawl_engine.state import StateBase
from backend.crawl_engine import engine as engine_module
from backend.crawl_engine.engine import EngineV2
from backend.models import Job


def test_stop_on_seen_ratio_triggers_error(monkeypatch):
    # stub scorer
    monkeypatch.setattr(engine_module, "get_nlp_scorer", lambda: None)
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)
    StateBase.metadata.create_all(db_engine)
    Session = sessionmaker(bind=db_engine)
    session = Session()

    # seed existing job
    job_key = Job.generate_key("Title", "Company", "https://example.com", "test")
    existing = Job(
        job_hash=job_key,
        job_key=job_key,
        title="Title",
        company="Company",
        location="Remote",
        description="Desc",
        url="https://example.com",
        source="test",
        job_fingerprint="fp1",
        last_seen_at=datetime.now(timezone.utc),
    )
    session.add(existing)
    session.commit()

    def crawler(cursor=None):
        return [
            {
                "title": "Title",
                "company": "Company",
                "location": "Remote",
                "description": "Desc",
                "url": "https://example.com",
                "source": "test",
                "post_date": datetime.now(timezone.utc).isoformat(),
            }
        ]

    eng = EngineV2(db=session, ignore_cooldown=True)
    asyncio.run(eng._run_source("test", crawler))

    errors = eng.metrics.source["test"]["errors"]
    assert any("stop_on_seen_ratio_triggered" in e for e in errors)
    session.close()
