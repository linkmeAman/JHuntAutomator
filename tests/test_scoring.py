from backend.crawler import JobCrawler
from backend.models import Job


class DummyScorer:
    def score(self, text: str) -> float:
        return 0.5


def test_relevance_score_combines_keywords_and_semantics():
    crawler = JobCrawler(
        keywords=["Python"],
        locations=["Remote"],
        max_jobs=5,
        nlp_scorer=DummyScorer(),
    )

    job_data = {
        "title": "Senior Python Engineer",
        "company": "Example Inc.",
        "location": "Remote",
        "description": "Looking for a Python expert.",
        "url": "https://example.com/job/123",
        "source": "Test",
    }

    score, matched = crawler.calculate_relevance_score(job_data)

    assert score > 0.5
    assert "Python" in matched


def test_hash_generation_is_stable():
    hash_1 = Job.generate_hash("Title", "Company", "https://example.com")
    hash_2 = Job.generate_hash("Title", "Company", "https://example.com")

    assert hash_1 == hash_2
