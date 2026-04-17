"""One-shot: crawl PartSelect, parse part pages, upsert SQLite + Chroma.

Usage:
    uv run python scripts/run_scrape.py              # full run
    uv run python scripts/run_scrape.py --limit 20   # cap parts for testing
    uv run python scripts/run_scrape.py --reset      # clear Chroma first
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Allow `from app...` imports when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402

from app.scraper.ingest import run  # noqa: E402
from app.scraper.seeds import ANCHOR_MODELS, ANCHOR_PART_SLUGS  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Cap total parts ingested")
    parser.add_argument("--reset", action="store_true", help="Clear Chroma before ingesting")
    parser.add_argument("--skip-vectors", action="store_true", help="Scrape + SQLite only")
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args()

    load_dotenv(override=True)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    asyncio.run(
        run(
            anchor_part_slugs=ANCHOR_PART_SLUGS,
            anchor_models=ANCHOR_MODELS,
            max_parts=args.limit,
            reset_vectors=args.reset,
            skip_vectors=args.skip_vectors,
        )
    )


if __name__ == "__main__":
    main()
