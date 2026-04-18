"""Install-specific view of a part record."""

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
        "install_difficulty": part.install_difficulty,
        "install_time_min": part.install_time_min,
        "install_time_source": "repair_rating" if part.install_time_min else None,
        "install_steps": part.install_steps,
        "install_steps_source": "customer_repair_stories",
        "install_tools": part.install_tools,
        "install_tools_listed": len(part.install_tools) > 0,
        "install_tools_note": (
            None
            if part.install_tools
            else "No tools were listed in the available repair stories."
        ),
        "install_video_url": part.install_video_url,
        "safety_flags": part.safety_flags,
        "source_url": part.source_url,
    }


SCHEMA = {
    "name": "get_install_guide",
    "description": (
        "Return install instructions, difficulty, time estimate, required "
        "tools, safety notes, and (if available) a video URL for a specific "
        "part. Steps are crowd-sourced repair stories from PartSelect — real "
        "customer write-ups, not official docs. Always cite the source_url. "
        "Returns {found: false} if the part isn't indexed."
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
