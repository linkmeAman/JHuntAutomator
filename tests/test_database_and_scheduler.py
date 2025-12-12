import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from backend import main
from backend.models import Base, Job


def test_duplicate_job_hash_rejected(tmp_path):
    db_url = f"sqlite:///{tmp_path/'test.db'}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    job_hash = Job.generate_hash("Title", "Company", "https://example.com", "Source")

    job = Job(
        job_hash=job_hash,
        title="Title",
        company="Company",
        location="Remote",
        description="Desc",
        url="https://example.com",
        source="Source",
    )
    session.add(job)
    session.commit()

    duplicate = Job(
        job_hash=job_hash,
        title="Title 2",
        company="Company",
        location="Remote",
        description="Desc",
        url="https://example.com/2",
        source="Source",
    )
    session.add(duplicate)

    with pytest.raises(IntegrityError):
        session.commit()


def test_scheduler_not_started_in_workflow_mode(monkeypatch):
    started = {"flag": False}

    def fake_start(app):
        started["flag"] = True

    original_mode = main.settings.CRAWL_MODE
    try:
        main.settings.CRAWL_MODE = "workflow"
        monkeypatch.setattr(main, "start_scheduler", fake_start)
        main.start_scheduler_if_configured(app=None)
    finally:
        main.settings.CRAWL_MODE = original_mode

    assert started["flag"] is False
