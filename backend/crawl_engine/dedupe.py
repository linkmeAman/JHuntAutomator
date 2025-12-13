from backend.models import Job


def compute_keys(raw_job):
    job_key = Job.generate_key(
        raw_job.get("title", ""),
        raw_job.get("company", ""),
        raw_job.get("url", ""),
        raw_job.get("source", ""),
        raw_job.get("post_date"),
        raw_job.get("location"),
    )
    job_hash = Job.generate_hash(
        raw_job.get("title", ""),
        raw_job.get("company", ""),
        raw_job.get("url", ""),
        raw_job.get("source", ""),
        raw_job.get("post_date"),
        raw_job.get("location"),
    )
    return job_key, job_hash


def fingerprint_from_payload(payload: dict) -> str:
    return payload.get("job_fingerprint") or Job.generate_hash(
        payload.get("title", ""),
        payload.get("company", ""),
        payload.get("location", "") + payload.get("description", ""),
        payload.get("source", ""),
    )
