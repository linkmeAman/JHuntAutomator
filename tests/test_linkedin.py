from pathlib import Path
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.linkedin_email_ingest import parse_eml
from backend.sources import linkedin
from backend import crawl_runner
from backend.models import Base, Settings as SettingsModel, Job


def load_fixture(name: str) -> str:
    return Path(__file__).parent.joinpath("fixtures", name).read_text(encoding="utf-8")


def test_linkedin_email_parses_job():
    eml = load_fixture("linkedin_job_alert_email.eml")
    jobs = parse_eml(eml)
    assert jobs
    assert jobs[0]["url"].startswith("https://www.linkedin.com/jobs/view/")
    assert jobs[0]["title"]


def test_linkedin_hash_stable():
    h1 = Job.generate_hash("Python Engineer", "LinkedIn", "https://www.linkedin.com/jobs/view/123456", "linkedin")
    h2 = Job.generate_hash("Python Engineer", "LinkedIn", "https://www.linkedin.com/jobs/view/123456", "linkedin")
    assert h1 == h2


def test_linkedin_crawl_refuses_when_not_allowed(tmp_path):
    db_url = f"sqlite:///{tmp_path/'linkedin.db'}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    session.add(SettingsModel(key="sources", value=json.dumps({"linkedin": True})))
    session.add(SettingsModel(key="keywords", value=json.dumps(["Python"])))
    session.add(SettingsModel(key="locations", value=json.dumps(["Remote"])))
    session.add(SettingsModel(key="greenhouse_boards", value=json.dumps([])))
    session.add(SettingsModel(key="linkedin_mode", value=json.dumps("whitelist_crawl")))
    session.add(SettingsModel(key="linkedin_crawl", value=json.dumps({"allowed": False, "seed_urls": []})))
    session.commit()

    # Ensure no jobs added when crawl not allowed
    def fake_fetch_jobs(settings):
        return linkedin.fetch_jobs(settings)

    crawl_runner.execute_crawl(session, send_notifications=False)
    assert session.query(Job).count() == 0
