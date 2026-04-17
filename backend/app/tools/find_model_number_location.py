"""Tell the user where to find the model/serial tag on their appliance."""

from __future__ import annotations

from app.store import model_locations


async def run(appliance_type: str, brand: str | None = None) -> dict:
    if appliance_type not in ("fridge", "dishwasher"):
        return {
            "appliance_type": appliance_type,
            "brand": brand,
            "description": "This demo only covers refrigerators and dishwashers.",
            "is_brand_specific": False,
        }
    loc = model_locations.lookup(brand, appliance_type)  # type: ignore[arg-type]
    key = (brand.lower().strip(), appliance_type) if brand else None
    return {
        "appliance_type": appliance_type,
        "brand": brand,
        "description": loc,
        "is_brand_specific": bool(key and key in model_locations.LOCATIONS),
    }


SCHEMA = {
    "name": "find_model_number_location",
    "description": (
        "Describe where the model/serial number sticker is located on the "
        "user's appliance, so they can read it off and give us their model. "
        "Use this when the user doesn't know their model number. Brand-"
        "specific when possible, generic fallback otherwise."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "appliance_type": {
                "type": "string",
                "enum": ["fridge", "dishwasher"],
            },
            "brand": {
                "type": "string",
                "description": "Appliance brand, e.g. 'Whirlpool'. Optional.",
            },
        },
        "required": ["appliance_type"],
    },
}
