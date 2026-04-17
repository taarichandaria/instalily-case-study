"""Full record for a single part, with related parts resolved to name+price."""

from __future__ import annotations

from app.store import parts_db


async def run(ps_number: str) -> dict:
    ps = ps_number.strip().upper()
    part = parts_db.get_part(ps)
    if part is None:
        return {"ps_number": ps, "found": False}

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
        "you_may_also_need": [rp.model_dump() for rp in part.you_may_also_need],
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
