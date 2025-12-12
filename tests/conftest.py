import json
from pathlib import Path

import pytest
import requests


class _DummyResponse:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def json(self):
        return json.loads(self.text)


@pytest.fixture()
def cached_http(monkeypatch):
    """Cache HTTP responses in tests to avoid network flakiness."""
    cache = {}
    fixtures_dir = Path(__file__).parent / "fixtures"

    def fake_get(url, *args, **kwargs):
        if url in cache:
            return cache[url]

        if "weworkremotely" in url:
            text = fixtures_dir.joinpath("weworkremotely.xml").read_text(encoding="utf-8")
            cache[url] = _DummyResponse(text)
            return cache[url]

        if "greenhouse" in url:
            text = fixtures_dir.joinpath("greenhouse.json").read_text(encoding="utf-8")
            cache[url] = _DummyResponse(text)
            return cache[url]

        real = requests.get(url, *args, **kwargs)
        cache[url] = real
        return real

    monkeypatch.setattr("backend.crawler.requests.get", fake_get)
    return cache
