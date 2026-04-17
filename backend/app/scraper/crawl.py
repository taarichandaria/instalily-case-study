"""Async PartSelect fetcher with on-disk HTML cache.

Uses curl_cffi with browser TLS impersonation — see
memory/feedback_partselect_scraping.md for why.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from pathlib import Path

from curl_cffi.requests import AsyncSession

log = logging.getLogger(__name__)

BASE = "https://www.partselect.com"
DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
CACHE_DIR = DATA_ROOT / "raw_html"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

PS_NUMBER_RE = re.compile(r"PS(\d{6,})")


def _cache_key(url: str) -> Path:
    """Derive a cache filename. For part/model pages we use the identifier; for
    everything else we hash the URL."""
    m = PS_NUMBER_RE.search(url)
    if m:
        return CACHE_DIR / f"part_PS{m.group(1)}.html"
    m = re.search(r"/Models/([A-Z0-9]+)", url)
    if m:
        return CACHE_DIR / f"model_{m.group(1)}.html"
    h = hashlib.sha1(url.encode()).hexdigest()[:12]
    return CACHE_DIR / f"misc_{h}.html"


class Crawler:
    def __init__(self, concurrency: int = 4, delay_s: float = 0.6) -> None:
        self._sem = asyncio.Semaphore(concurrency)
        self._delay = delay_s
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> "Crawler":
        self._session = AsyncSession(impersonate="chrome")
        await self._session.__aenter__()
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._session is not None:
            await self._session.__aexit__(*exc)
            self._session = None

    async def fetch(self, url: str, *, force: bool = False) -> str | None:
        """Return HTML for `url`. Uses disk cache unless `force=True`."""
        cache = _cache_key(url)
        if not force and cache.exists():
            return cache.read_text()
        if self._session is None:
            raise RuntimeError("Crawler used outside async context manager")
        async with self._sem:
            try:
                r = await self._session.get(
                    url, headers=HEADERS, allow_redirects=True, timeout=30
                )
            except Exception as e:  # noqa: BLE001
                log.warning("fetch failed %s: %s", url, e)
                return None
            await asyncio.sleep(self._delay)
            if r.status_code != 200 or len(r.text) < 2000:
                log.warning("fetch %s -> status=%s size=%d", url, r.status_code, len(r.text))
                return None
            cache.write_text(r.text)
            return r.text


def part_url(slug: str) -> str:
    """Accepts either a full URL, a `/PSxxx-...htm` path, or a bare PS number."""
    if slug.startswith("http"):
        return slug
    if slug.startswith("/"):
        return BASE + slug
    if PS_NUMBER_RE.match(slug):
        return f"{BASE}/{slug}.htm"
    return f"{BASE}/{slug}"


def model_url(model_number: str) -> str:
    return f"{BASE}/Models/{model_number}/"
