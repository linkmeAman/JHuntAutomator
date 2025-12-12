from backend.models import Job
from backend.crawl_runner import execute_crawl
from backend.schemas import JobCreate
from backend.models import Base, Settings as SettingsModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json


def test_job_key_diff_urls(tmp_path, monkeypatch):
    h1 = Job.generate_key("Title", "Co", "https://example.com/a", "source")
    h2 = Job.generate_key("Title", "Co", "https://example.com/b", "source")
    assert h1 != h2


def test_low_score_still_stored(tmp_path, monkeypatch):
    db_url = f"sqlite:///{tmp_path/'low.db'}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(SettingsModel(key="sources", value=json.dumps({"remoteok": True})))
    session.add(SettingsModel(key="keywords", value=json.dumps(["Python"])))
    session.add(SettingsModel(key="locations", value=json.dumps(["Remote"])))
    session.add(SettingsModel(key="greenhouse_boards", value=json.dumps([])))
    session.commit()

    sample_job = JobCreate(
        title="Job",
        company="Co",
        location="Remote",
        description="desc",
        url="https://example.com/job",
        source="remoteok",
        job_hash=Job.generate_hash("Job", "Co", "https://example.com/job", "remoteok"),
        job_key=Job.generate_key("Job", "Co", "https://example.com/job", "remoteok"),
        relevance_score=0.1,
    )

    monkeypatch.setattr(
        "backend.crawl_runner.JobCrawler.crawl_remoteok", lambda self: [sample_job]
    )
    monkeypatch.setattr("backend.crawl_runner.get_nlp_scorer", lambda: None)
    result = execute_crawl(session, send_notifications=False, override_sources={"remoteok": True}, min_store_score=0.0)
    assert result.jobs_added == 1
