"""Boolean compatibility lookup against the SQLite compat table."""

from __future__ import annotations

from app.store import parts_db


async def run(ps_number: str, model_number: str) -> dict:
    ps = ps_number.strip().upper()
    mn = model_number.strip().upper()
    part = parts_db.get_part(ps)
    total = parts_db.compat_count(ps)
    if total == 0:
        status = "unknown"
    else:
        status = "yes" if parts_db.check_compat(ps, mn) else "no"
    return {
        "ps_number": ps,
        "model_number": mn,
        "status": status,
        "total_known_models": total,
        "part_name": part.name if part else None,
    }


SCHEMA = {
    "name": "check_compatibility",
    "description": (
        "Check whether a specific PartSelect part (ps_number) fits a specific "
        "appliance model (model_number). Returns 'yes', 'no', or 'unknown' "
        "(the latter means we have no compatibility data for that part yet — "
        "say so instead of guessing). Also returns the total number of known "
        "compatible models for that part, useful for confidence framing."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "ps_number": {
                "type": "string",
                "description": "PartSelect part number, e.g. PS11752778.",
            },
            "model_number": {
                "type": "string",
                "description": "Appliance model number, e.g. WDT780SAEM1.",
            },
        },
        "required": ["ps_number", "model_number"],
    },
}
