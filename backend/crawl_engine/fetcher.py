import asyncio
import random
import time
from typing import Optional, Dict

import certifi
import httpx
from backend.config import settings

class RateLimiter:
    def __init__(self, max_concurrent: int):
        self.sem = asyncio.Semaphore(max_concurrent)

    async def __aenter__(self):
        await self.sem.acquire()

    async def __aexit__(self, exc_type, exc, tb):
        self.sem.release()


class Fetcher:
    def __init__(self, max_concurrent_global: int = 10, per_domain: int = 2, min_delay_ms=600, max_delay_ms=1200):
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=40)
        timeout = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=30.0)
        verify_path = settings.CA_BUNDLE_PATH or certifi.where()
        self.client = httpx.AsyncClient(timeout=timeout, limits=limits, verify=verify_path)
        self.global_limit = RateLimiter(max_concurrent_global)
        self.domain_limits: Dict[str, RateLimiter] = {}
        self.min_delay_ms = min_delay_ms
        self.max_delay_ms = max_delay_ms

    async def fetch(self, url: str, headers: Optional[dict] = None, params: Optional[dict] = None, retries: int = 2):
        domain = httpx.URL(url).host or ""
        if domain not in self.domain_limits:
            self.domain_limits[domain] = RateLimiter(2)
        async with self.global_limit, self.domain_limits[domain]:
            await asyncio.sleep(random.uniform(self.min_delay_ms, self.max_delay_ms) / 1000.0)
            attempt = 0
            backoff = 1.0
            last_exc: Exception | None = None
            while attempt <= retries:
                try:
                    resp = await self.client.get(
                        url,
                        headers={
                            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
                            "Accept-Language": "en-US,en;q=0.8",
                            "Connection": "keep-alive",
                            **(headers or {}),
                        },
                        params=params,
                    )
                    return resp
                except Exception as exc:
                    last_exc = exc
                    await asyncio.sleep(backoff + random.uniform(0.2, 0.8))
                    backoff = min(backoff * 2, 8)
                    attempt += 1
            if last_exc:
                raise last_exc
            raise RuntimeError(f"HTTPX GET failed for {url}")

    async def close(self):
        await self.client.aclose()
