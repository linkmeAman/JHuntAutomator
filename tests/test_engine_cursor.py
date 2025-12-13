from datetime import datetime, timedelta, timezone

from backend.crawl_engine import engine as engine_module
from backend.crawl_engine.engine import EngineV2
from backend.crawl_engine.state import SourceState


class DummyDB:
    def __init__(self):
        self.actions = []

    def add(self, _):
        self.actions.append("add")

    def commit(self):
        self.actions.append("commit")


def test_compute_since_uses_lookback_when_no_cursor(monkeypatch):
    monkeypatch.setattr(engine_module, "get_nlp_scorer", lambda: None)
    engine = EngineV2(db=DummyDB(), ignore_cooldown=True)
    since = engine._compute_since({})
    now = datetime.utcnow()
    assert now - since >= timedelta(days=6)  # lookback default 7 days


def test_update_last_seen_advances_cursor(monkeypatch):
    monkeypatch.setattr(engine_module, "get_nlp_scorer", lambda: None)
    engine = EngineV2(db=DummyDB(), ignore_cooldown=True)
    cursor = {}
    class Raw:
        post_date = datetime.now(timezone.utc).isoformat()
    engine._update_last_seen(cursor, Raw())
    assert "last_max_post_date_seen" in cursor
