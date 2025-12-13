import time
from collections import defaultdict


class Metrics:
    def __init__(self):
        self.source = defaultdict(lambda: {
            "fetched_count": 0,
            "requested_pages": 0,
            "pages_fetched": 0,
            "http_status_counts": {},
            "jobs_parsed_count": 0,
            "jobs_normalized_count": 0,
            "jobs_scored_count": 0,
            "jobs_above_threshold_count": 0,
            "jobs_insert_attempted_count": 0,
            "jobs_inserted_count": 0,
            "jobs_updated_count": 0,
            "jobs_deduped_count": 0,
            "matched_count": 0,
            "not_modified": False,
            "errors": [],
            "latencies_ms": [],
            "cache_hits": 0,
            "retries": 0,
        })

    def record_latency(self, source: str, ms: float):
        self.source[source]["latencies_ms"].append(ms)

    def to_json(self):
        out = {}
        for src, data in self.source.items():
            out[src] = data
        return out
