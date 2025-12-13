import logging
import random
import time
from typing import Optional

import certifi
import requests
from backend.config import settings

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}


class SourceBlockedError(Exception):
    """Raised when a source appears to block or captcha the request."""


def get(url: str, *, timeout: tuple[int, int] = (10, 30), headers: Optional[dict] = None, retries: int = 2, verify: Optional[str | bool] = None, cache: Optional[dict] = None) -> requests.Response:
    merged_headers = {**DEFAULT_HEADERS, **(headers or {})}
    cache = cache or {}
    if cache.get("etag"):
        merged_headers["If-None-Match"] = cache["etag"]
    if cache.get("last_modified"):
        merged_headers["If-Modified-Since"] = cache["last_modified"]
    attempt = 0
    backoff = 1.0
    last_exc: Exception | None = None
    verify_path = verify if verify is not None else (settings.CA_BUNDLE_PATH or certifi.where())

    while attempt <= retries:
        try:
            resp = requests.get(url, headers=merged_headers, timeout=timeout, verify=verify_path)
            if resp.headers.get("ETag"):
                cache["etag"] = resp.headers.get("ETag")
            if resp.headers.get("Last-Modified"):
                cache["last_modified"] = resp.headers.get("Last-Modified")
            return resp
        except Exception as exc:
            last_exc = exc
            sleep_for = backoff + random.uniform(0.2, 0.8)
            time.sleep(sleep_for)
            backoff *= 2
            attempt += 1

    if last_exc:
        raise last_exc
    raise RuntimeError("HTTP GET failed without exception")
