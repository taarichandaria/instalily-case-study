"""Pipeline orchestration: crawl -> parse -> upsert to SQLite + Chroma."""

from __future__ import annotations

import asyncio
import logging
from typing import Iterable

from app.schemas import Part
from app.scraper.crawl import Crawler, model_url, part_url
from app.scraper.parse import parse_model_parts_page, parse_part_page
from app.store import chroma_index, parts_db

log = logging.getLogger(__name__)


async def _gather_model_parts(
    crawler: Crawler, models: Iterable[str]
) -> dict[str, dict[str, str]]:
    """For each model number, return a map of PS number -> URL slug for the
    parts listed on its first page."""
    out: dict[str, dict[str, str]] = {}

    async def one(model_number: str) -> None:
        html = await crawler.fetch(model_url(model_number))
        if html is None:
            log.warning("model page fetch failed: %s", model_number)
            return
        out[model_number] = parse_model_parts_page(html, model_number)
        log.info("model %s -> %d parts on first page", model_number, len(out[model_number]))

    await asyncio.gather(*(one(m) for m in models))
    return out


async def _ingest_part(crawler: Crawler, ps_number: str, slug: str) -> Part | None:
    """Fetch + parse + persist one part. `slug` is either a full URL, a
    `/PSxxx-...htm` path, or a bare PS number (which usually 500s — avoid)."""
    url = part_url(slug)
    html = await crawler.fetch(url)
    if html is None:
        return None
    part = parse_part_page(html, url)
    if part is None:
        log.warning("parse returned None for %s", ps_number)
        return None
    parts_db.upsert_part(part)
    parts_db.upsert_compat(part.ps_number, part.compat_models)
    return part


async def run(
    *,
    anchor_part_slugs: dict[str, str],
    anchor_models: dict[str, str],
    max_parts: int | None = None,
    reset_vectors: bool = False,
    skip_vectors: bool = False,
) -> None:
    parts_db.init_db()
    if reset_vectors and not skip_vectors:
        chroma_index.reset()

    async with Crawler() as crawler:
        # 1. Resolve anchor models -> candidate PS numbers + slugs + compat pairs
        log.info("fetching %d anchor model pages…", len(anchor_models))
        model_parts = await _gather_model_parts(crawler, anchor_models.keys())

        # Persist (part, model) pairs eagerly so compat checks work even if the
        # individual part pages fail later.
        for model_number, ps_map in model_parts.items():
            for ps in ps_map:
                parts_db.upsert_compat(ps, [model_number])

        # 2. Build the crawl queue as (ps_number, slug) pairs. Anchor parts win
        # if their slug differs from what a model page listed.
        queue: list[tuple[str, str]] = []
        seen: set[str] = set()

        def enqueue(ps: str, slug: str) -> None:
            if ps in seen:
                return
            seen.add(ps)
            queue.append((ps, slug))

        for ps, slug in anchor_part_slugs.items():
            enqueue(ps, slug)
        for ps_map in model_parts.values():
            for ps, slug in ps_map.items():
                enqueue(ps, slug)

        if max_parts is not None:
            queue = queue[:max_parts]
        log.info("crawl queue: %d parts", len(queue))

        # 3. Fetch + parse part pages
        processed: list[Part] = []

        async def worker(ps: str, slug: str) -> None:
            part = await _ingest_part(crawler, ps, slug)
            if part is not None:
                processed.append(part)

        # Run with bounded concurrency (Crawler's own semaphore rate-limits fetches).
        # Use gather in chunks to avoid creating thousands of tasks at once.
        chunk_size = 20
        for i in range(0, len(queue), chunk_size):
            chunk = queue[i : i + chunk_size]
            await asyncio.gather(*(worker(ps, slug) for ps, slug in chunk))
            log.info("ingested %d / %d parts", min(i + chunk_size, len(queue)), len(queue))

        # 4. Embed + upsert to Chroma in batches
        if skip_vectors:
            log.info("skipping vector index (skip_vectors=True)")
        else:
            log.info("embedding + upserting %d parts to Chroma…", len(processed))
            for i in range(0, len(processed), 50):
                batch = processed[i : i + 50]
                chroma_index.upsert_parts(batch)

    vec_size = chroma_index.size() if not skip_vectors else 0
    log.info("done. total parts in sqlite: %d, chroma: %d",
             parts_db.total_parts(), vec_size)
