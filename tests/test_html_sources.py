from pathlib import Path

from backend.sources import naukri, shine, timesjobs, remote_co
from backend.models import Job


def load(name: str) -> str:
    return Path(__file__).parent.joinpath("fixtures", name).read_text(encoding="utf-8")


def test_naukri_parse():
    html = load("naukri_search.html")
    jobs = naukri.parse_jobs(html)
    assert jobs
    assert jobs[0]["title"]
    assert jobs[0]["source"] == "naukri"


def test_shine_parse():
    html = load("shine_search.html")
    jobs = shine.parse_jobs(html)
    assert jobs
    assert jobs[0]["title"]
    assert jobs[0]["source"] == "shine"


def test_timesjobs_parse():
    html = load("timesjobs_search.html")
    jobs = timesjobs.parse_jobs(html)
    assert jobs
    assert jobs[0]["title"]
    assert jobs[0]["source"] == "timesjobs"


def test_remote_co_parse():
    html = load("remote_co_search.html")
    jobs = remote_co.parse_jobs(html)
    assert jobs
    assert jobs[0]["source"] == "remote_co"


def test_hash_stability_for_parsed_jobs():
    h1 = Job.generate_hash("Senior Engineer", "NaukriCorp", "https://naukri.com/job1", "naukri")
    h2 = Job.generate_hash("Senior Engineer", "NaukriCorp", "https://naukri.com/job1", "naukri")
    assert h1 == h2
