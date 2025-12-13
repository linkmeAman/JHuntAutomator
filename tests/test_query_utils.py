from backend.crawl_engine.query_utils import generate_queries


def test_generate_queries_bounded_and_unique():
    keywords = ["Python", "React", "Node"]
    qs = generate_queries(keywords, india_mode=False, max_queries=3, variants=3)
    assert len(qs) == 3
    assert qs[0].startswith("Python")
    assert len(set(qs)) == len(qs)


def test_generate_queries_india_mode_adds_city():
    keywords = ["Backend"]
    qs = generate_queries(keywords, india_mode=True, max_queries=3, variants=1)
    # should include one city variant bounded by max_queries
    assert len(qs) == 3
    assert any("Backend" in q for q in qs)
