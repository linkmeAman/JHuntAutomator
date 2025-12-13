import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend import crawl_runner
from backend.models import Base, Settings as SettingsModel
from backend.sources import remotive


def test_pipeline_dedupes_new_sources(tmp_path, monkeypatch):
    db_url = f"sqlite:///{tmp_path/'pipeline.db'}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    settings = {"remotive": True}
    session.add(SettingsModel(key="sources", value=json.dumps(settings)))
    session.add(SettingsModel(key="keywords", value=json.dumps(["Python"])))
    session.add(SettingsModel(key="locations", value=json.dumps(["Remote"])))
    session.add(SettingsModel(key="greenhouse_boards", value=json.dumps([])))
    session.commit()

    fixture_jobs = [
        {
            "title": "Python Developer",
            "company": "RemotiveCo",
            "location": "Remote",
            "description": "Build APIs",
            "url": "https://remotive.com/job/1",
            "source": "remotive",
            "remote": True,
        }
    ]

    monkeypatch.setattr(remotive, "fetch_jobs", lambda settings: fixture_jobs)
    monkeypatch.setattr(crawl_runner, "get_nlp_scorer", lambda: None)

    result1 = crawl_runner.execute_crawl(session, send_notifications=False, override_sources={"remotive": True})
    result2 = crawl_runner.execute_crawl(session, send_notifications=False, override_sources={"remotive": True})

    assert result1.jobs_added == 1
    assert result2.jobs_added == 0
