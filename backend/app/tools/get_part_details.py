"""Full record for a single part, with related parts resolved to name+price."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.store import parts_db

BASE = "https://www.partselect.com"
PS_HREF_RE = re.compile(r"/PS(\d{6,})[-.]")
RAW_HTML_DIR = Path(__file__).resolve().parents[2] / "data" / "raw_html"


def _section_content(soup: BeautifulSoup, anchor_id: str) -> Tag | None:
    anchor = soup.find(id=anchor_id)
    if anchor is None:
        return None
    nxt = anchor.find_next_sibling()
    return nxt if isinstance(nxt, Tag) else None


def _related_parts_from_saved_html(ps_number: str) -> dict[str, dict[str, str]]:
    path = RAW_HTML_DIR / f"part_{ps_number}.html"
    if not path.exists():
        return {}

    soup = BeautifulSoup(
        path.read_text(encoding="utf-8", errors="ignore"),
        "lxml",
    )
    related = _section_content(soup, "RelatedParts")
    if related is None:
        return {}

    resolved: dict[str, dict[str, str]] = {}
    for card in related.select(".pd__related-part"):
        links = card.find_all("a", href=PS_HREF_RE)
        if not links:
            continue
        href = links[0].get("href", "")
        match = PS_HREF_RE.search(href)
        if not match:
            continue
        ps = f"PS{match.group(1)}"

        entry: dict[str, str] = {}
        if href:
            entry["source_url"] = urljoin(BASE, href)

        img = card.find("img")
        if img:
            src = img.get("data-src") or img.get("src")
            if isinstance(src, str) and src and not src.startswith("data:image/"):
                entry["image_url"] = src if src.startswith("http") else urljoin(BASE, src)

        if entry:
            resolved[ps] = entry

    return resolved


async def run(ps_number: str) -> dict:
    ps = ps_number.strip().upper()
    part = parts_db.get_part(ps)
    if part is None:
        return {"ps_number": ps, "found": False}

    related_index = parts_db.get_parts([rp.ps_number for rp in part.you_may_also_need])
    related_saved = _related_parts_from_saved_html(ps)

    you_may_also_need: list[dict] = []
    for related in part.you_may_also_need:
        indexed = related_index.get(related.ps_number)
        saved = related_saved.get(related.ps_number, {})
        merged = related.model_dump()
        merged["source_url"] = (
            related.source_url
            or (indexed.source_url if indexed else None)
            or saved.get("source_url")
        )
        merged["image_url"] = (
            related.image_url
            or (indexed.image_url if indexed else None)
            or saved.get("image_url")
        )
        you_may_also_need.append(merged)

    return {
        "ps_number": part.ps_number,
        "found": True,
        "name": part.name,
        "oem_number": part.oem_number,
        "brand": part.brand,
        "appliance_type": part.appliance_type,
        "price_usd": part.price_usd,
        "in_stock": part.in_stock,
        "description": part.description,
        "symptoms_fixed": part.symptoms_fixed,
        "install_difficulty": part.install_difficulty,
        "install_time_min": part.install_time_min,
        "image_url": part.image_url,
        "source_url": part.source_url,
        "you_may_also_need_source": "PartSelect You May Also Need",
        "you_may_also_need": you_may_also_need,
        "total_known_compat_models": parts_db.compat_count(part.ps_number),
    }


SCHEMA = {
    "name": "get_part_details",
    "description": (
        "Fetch the full record for a specific PartSelect part by ps_number. "
        "Use this when the user references a specific part, or after "
        "search_parts / diagnose_symptom to get install difficulty, price, "
        "related parts, etc. Returns {found: false} if the part isn't in the "
        "index — fall back to live_fetch_part when that happens."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "ps_number": {
                "type": "string",
                "description": "PartSelect part number, e.g. PS11752778.",
            },
        },
        "required": ["ps_number"],
    },
}
