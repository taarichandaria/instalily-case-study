"""Live, model-scoped PartSelect search for compatible parts."""

from __future__ import annotations

import asyncio

from app.scraper.crawl import Crawler, model_search_url, part_url
from app.scraper.parse import parse_model_parts_page, parse_part_page
from app.store import parts_db


async def _load_part(crawler: Crawler, ps_number: str, slug: str, model_number: str):
    part = parts_db.get_part(ps_number)
    if part is not None:
        parts_db.upsert_compat(ps_number, [model_number])
        return part

    html = await crawler.fetch(part_url(slug))
    if html is None:
        return None

    part = parse_part_page(html, part_url(slug))
    if part is None:
        return None

    parts_db.upsert_part(part)
    parts_db.upsert_compat(part.ps_number, set(part.compat_models + [model_number]))
    return part


async def run(model_number: str, query: str, limit: int = 5) -> dict:
    mn = model_number.strip().upper()
    q = query.strip()
    max_results = min(max(limit, 1), 8)
    search_url = model_search_url(mn, q)
    if not q:
        return {"model_number": mn, "query": q, "found": False, "results": []}

    async with Crawler() as crawler:
        html = await crawler.fetch(search_url, force=True)
        if html is None:
            return {
                "model_number": mn,
                "query": q,
                "found": False,
                "results": [],
                "error": "model search fetch failed",
            }

        ps_map = parse_model_parts_page(html, mn)
        if not ps_map:
            return {
                "model_number": mn,
                "query": q,
                "found": False,
                "results": [],
                "error": "no matching parts found on model page",
            }

        for ps_number in ps_map:
            parts_db.upsert_compat(ps_number, [mn])

        ordered = list(ps_map.items())[:max_results]
        fetched = await asyncio.gather(
            *(
                _load_part(crawler, ps_number, slug, mn)
                for ps_number, slug in ordered
            )
        )

    results: list[dict] = []
    for part in fetched:
        if part is None:
            continue
        results.append(
            {
                "ps_number": part.ps_number,
                "name": part.name,
                "brand": part.brand,
                "appliance_type": part.appliance_type,
                "price_usd": part.price_usd,
                "in_stock": part.in_stock,
                "image_url": part.image_url,
                "source_url": part.source_url,
                "compatibility_status": "yes",
                "model_number": mn,
            }
        )

    return {
        "model_number": mn,
        "query": q,
        "found": len(results) > 0,
        "total_matching_parts": len(ps_map),
        "results": results,
        "source_url": search_url,
    }


SCHEMA = {
    "name": "search_model_parts_live",
    "description": (
        "Search PartSelect live for parts already scoped to a specific model "
        "number, then return the top matching compatible parts with their live "
        "PartSelect URLs. Use this when the user's model number is known and "
        "the indexed search/compatibility path comes up empty or uncertain. "
        "Best with short part/category queries like 'ice maker', 'door shelf "
        "bin', 'water filter', or 'drain pump'."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "model_number": {
                "type": "string",
                "description": "Appliance model number, e.g. WRX735SDHZ.",
            },
            "query": {
                "type": "string",
                "description": (
                    "Short part/category search term to run within that model's "
                    "PartSelect parts page, e.g. 'ice maker'."
                ),
            },
            "limit": {
                "type": "integer",
                "description": "Maximum results to fetch and return (1-8).",
                "default": 5,
            },
        },
        "required": ["model_number", "query"],
    },
}
