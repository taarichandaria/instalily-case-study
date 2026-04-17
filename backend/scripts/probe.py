"""
One-off: fetch PartSelect flagship part + model pages, cache to disk, print
observations. Goal: confirm pages are server-rendered (no JS gate) and sketch
CSS selectors before writing parse.py.

Usage: uv run python scripts/probe.py
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession

HERE = Path(__file__).resolve().parent
CACHE = HERE.parent / "data" / "raw_html"
CACHE.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Sec-Ch-Ua": '"Not.A/Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

# Candidate URL patterns; PartSelect has changed schemes over time. We try
# each until one returns 200.
PART_URL_CANDIDATES = [
    "https://www.partselect.com/PS11752778-Whirlpool-WPW10321304-Refrigerator-Door-Shelf-Bin.htm",
    "https://www.partselect.com/PS11752778.htm",
]
MODEL_URL_CANDIDATES = [
    "https://www.partselect.com/Models/WDT780SAEM1/",
    "https://www.partselect.com/Models/WDT780SAEM1/Parts/",
]


async def fetch(session: AsyncSession, urls: list[str]) -> tuple[str, str] | None:
    for url in urls:
        try:
            r = await session.get(url, headers=HEADERS, allow_redirects=True, timeout=30)
        except Exception as e:  # noqa: BLE001
            print(f"  {url} -> error: {e}")
            continue
        print(f"  {url} -> {r.status_code} ({len(r.text)} bytes)")
        if r.status_code == 200 and len(r.text) > 5000:
            return str(r.url), r.text
    return None


def summarize(tag: str, html: str) -> None:
    soup = BeautifulSoup(html, "lxml")
    title = soup.find("title")
    h1 = soup.find("h1")
    print(f"[{tag}] <title>: {title.get_text(strip=True) if title else '(none)'}")
    print(f"[{tag}] <h1>: {h1.get_text(strip=True) if h1 else '(none)'}")

    # Price heuristic
    price_hits = soup.select('[class*="price" i], [itemprop="price"]')
    for p in price_hits[:5]:
        text = p.get_text(" ", strip=True)
        if "$" in text:
            print(f"[{tag}] price-ish: {text[:120]}")
            break

    # Install steps heuristic
    for sel in ["#Repair", "#Installation", '[class*="instruct" i]', '[class*="repair" i]']:
        hits = soup.select(sel)
        if hits:
            print(f"[{tag}] install section hit on {sel!r}: {len(hits)} el(s)")
            break

    # JS-gate detection: if body is tiny or mostly scripts, that's a red flag
    body = soup.find("body")
    if body:
        body_text = body.get_text(" ", strip=True)
        print(f"[{tag}] body text chars: {len(body_text)}")


async def main() -> None:
    async with AsyncSession(impersonate="chrome") as session:
        print("Fetching part page candidates…")
        part = await fetch(session, PART_URL_CANDIDATES)
        print("Fetching model page candidates…")
        model = await fetch(session, MODEL_URL_CANDIDATES)

    if part:
        url, html = part
        (CACHE / "probe_part_PS11752778.html").write_text(html)
        print(f"\nSaved part HTML ({len(html)} bytes) from {url}")
        summarize("PART", html)
    else:
        print("\nPART FETCH FAILED — no candidate returned 200 + body")

    if model:
        url, html = model
        (CACHE / "probe_model_WDT780SAEM1.html").write_text(html)
        print(f"\nSaved model HTML ({len(html)} bytes) from {url}")
        summarize("MODEL", html)
    else:
        print("\nMODEL FETCH FAILED — no candidate returned 200 + body")


if __name__ == "__main__":
    asyncio.run(main())
