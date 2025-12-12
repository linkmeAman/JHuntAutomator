import json
from pathlib import Path

from backend.models import Job
from backend.sources import remotive, workingnomads
from backend import crawl_runner


def load_fixture(name: str) -> str:
    return Path(__file__).parent.joinpath("fixtures", name).read_text(encoding="utf-8")


class DummyResp:
    def __init__(self, text: str, status: int = 200):
        self.text = text
        self.status_code = status

    def json(self):
        return json.loads(self.text)


def test_remotive_parser(monkeypatch):
    fixture = load_fixture("remotive.json")

    def fake_get(*args, **kwargs):
        return DummyResp(fixture)

    monkeypatch.setattr("backend.sources.remotive.requests.get", fake_get)

    jobs = remotive.fetch_jobs(settings=None)
    assert jobs
    assert jobs[0]["source"] == "remotive"
    assert jobs[0]["url"]


def test_workingnomads_parser(monkeypatch):
    fixture = load_fixture("workingnomads.json")

    def fake_get(*args, **kwargs):
        return DummyResp(fixture)

    monkeypatch.setattr("backend.sources.workingnomads.requests.get", fake_get)

    jobs = workingnomads.fetch_jobs(settings=None)
    assert jobs
    assert jobs[0]["source"] == "workingnomads"
    assert jobs[0]["url"]


def test_hash_stability_new_sources():
    h1 = Job.generate_hash("Python Developer", "RemotiveCo", "https://example.com/job", "remotive")
    h2 = Job.generate_hash("Python Developer", "RemotiveCo", "https://example.com/job", "remotive")
    assert h1 == h2
