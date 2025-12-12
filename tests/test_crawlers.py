from backend.crawler import JobCrawler


def test_weworkremotely_rss_parser_returns_jobs(cached_http):
    crawler = JobCrawler(
        keywords=["Python"],
        locations=["Remote"],
        max_jobs=5,
        nlp_scorer=None,
    )

    jobs = crawler.crawl_weworkremotely_rss()

    assert jobs, "Expected at least one job from RSS fixture"
    assert jobs[0].source == "WeWorkRemotely"


def test_greenhouse_parser_returns_jobs(cached_http):
    crawler = JobCrawler(
        keywords=["Engineer"],
        locations=["Remote"],
        max_jobs=5,
        nlp_scorer=None,
        greenhouse_boards=[{"name": "Example", "board_url": "https://boards.greenhouse.io/example"}],
    )

    jobs = crawler.crawl_greenhouse_boards()

    assert jobs, "Expected at least one job from Greenhouse fixture"
    assert jobs[0].source_detail == "Example"
