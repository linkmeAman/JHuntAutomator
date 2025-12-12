import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend import crawl_runner
from backend.models import Base, CrawlRun, Job, Settings as SettingsModel
from backend.schemas import JobCreate


def _build_session(tmp_path):
    db_url = f"sqlite:///{tmp_path/'runs.db'}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _stub_job(source: str = "RemoteOK"):
    job_hash = Job.generate_hash("Role", "Company", "https://example.com", source)
    return JobCreate(
        title="Role",
        company="Company",
        location="Remote",
        description="Desc",
        url="https://example.com",
        source=source,
        job_hash=job_hash,
        relevance_score=2.0,
        keywords_matched="Role",
    )


def test_execute_crawl_creates_run_record(tmp_path, monkeypatch):
    session = _build_session(tmp_path)
    session.add(SettingsModel(key="sources", value=json.dumps({"remoteok": True, "weworkremotely": False, "indeed": False, "greenhouse": False})))
    session.commit()

    monkeypatch.setattr(crawl_runner, "get_nlp_scorer", lambda: None)
    monkeypatch.setattr(
        crawl_runner.JobCrawler,
        "crawl_remoteok",
        lambda self: [_stub_job("RemoteOK")],
    )

    result = crawl_runner.execute_crawl(session, send_notifications=False)

    assert result.jobs_added == 1
    runs = session.query(CrawlRun).all()
    assert len(runs) == 1
    run = runs[0]
    assert json.loads(run.sources_attempted) == ["remoteok"]
    assert run.inserted_new_count == 1


def test_execute_crawl_records_failed_source(tmp_path, monkeypatch):
    session = _build_session(tmp_path)
    session.add(SettingsModel(key="sources", value=json.dumps({"remoteok": True, "greenhouse": True, "weworkremotely": False, "indeed": False})))
    session.commit()

    monkeypatch.setattr(crawl_runner, "get_nlp_scorer", lambda: None)
    monkeypatch.setattr(
        crawl_runner.JobCrawler,
        "crawl_remoteok",
        lambda self: [_stub_job("RemoteOK")],
    )
    monkeypatch.setattr(
        crawl_runner.JobCrawler,
        "crawl_greenhouse_boards",
        lambda self: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    crawl_runner.execute_crawl(session, send_notifications=False)

    run = session.query(CrawlRun).first()
    failures = json.loads(run.sources_failed)
    assert any(item["source"] == "greenhouse" for item in failures)


def test_notifications_gated_when_disabled(monkeypatch):
    from backend.notifications import NotificationService
    from backend.models import CrawlRun

    sent = {"email": False, "telegram": False}

    notifier = NotificationService()
    notifier.notifications_enabled = False

    monkeypatch.setattr(notifier, "_send_email", lambda *args, **kwargs: sent.__setitem__("email", True))
    monkeypatch.setattr(notifier, "_send_telegram", lambda *args, **kwargs: sent.__setitem__("telegram", True))

    run = CrawlRun(
        run_id="123",
        started_at=datetime.now(timezone.utc),
        sources_failed=json.dumps([{"source": "remoteok", "error": "timeout"}]),
        inserted_new_count=0,
    )

    notifier.send_run_alerts(run)

    assert sent["email"] is False
    assert sent["telegram"] is False
