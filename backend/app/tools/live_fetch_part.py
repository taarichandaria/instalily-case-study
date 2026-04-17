"""Fallback: fetch + parse a part from PartSelect live, bypassing the index."""

from __future__ import annotations

from app.scraper.crawl import Crawler, part_url
from app.scraper.parse import parse_part_page
from app.store import parts_db


async def run(ps_number_or_slug: str) -> dict:
    """`ps_number_or_slug` accepts bare PS numbers, URL paths, or full URLs.
    Bare PS numbers usually 500 on PartSelect — prefer a slug if you have one."""
    slug = ps_number_or_slug.strip()
    url = part_url(slug)
    async with Crawler() as crawler:
        html = await crawler.fetch(url, force=True)
    if html is None:
        return {"input": slug, "found": False, "error": "fetch failed"}

    part = parse_part_page(html, url)
    if part is None:
        return {"input": slug, "found": False, "error": "parse failed"}

    # Persist so follow-up tool calls hit the index path
    parts_db.upsert_part(part)
    parts_db.upsert_compat(part.ps_number, part.compat_models)

    return {
        "input": slug,
        "found": True,
        "ps_number": part.ps_number,
        "name": part.name,
        "brand": part.brand,
        "appliance_type": part.appliance_type,
        "price_usd": part.price_usd,
        "in_stock": part.in_stock,
        "source_url": part.source_url,
    }


SCHEMA = {
    "name": "live_fetch_part",
    "description": (
        "Fallback when get_part_details returns {found: false} or the user "
        "references a part we haven't indexed. Fetches and parses the part "
        "page directly from PartSelect, then adds it to the index so follow-"
        "up tool calls can use it. Accepts a PS number (e.g. 'PS11752778') "
        "or a PartSelect URL/slug."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "ps_number_or_slug": {
                "type": "string",
                "description": (
                    "A PartSelect part identifier — PS number, URL path "
                    "(`/PS...-slug.htm`), or full URL."
                ),
            },
        },
        "required": ["ps_number_or_slug"],
    },
}
