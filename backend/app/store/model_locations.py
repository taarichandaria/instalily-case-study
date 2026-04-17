"""Static map of where to find the model/serial tag on common appliances.

Covers the top brands PartSelect serves. Extensible: add a new row when we
encounter a brand we don't have. The agent exposes this via the
`find_model_number_location` tool.
"""

from __future__ import annotations

from typing import Literal

ApplianceType = Literal["fridge", "dishwasher"]

_DEFAULT_FRIDGE = (
    "On most refrigerators, look inside the fresh-food compartment for a tag "
    "on the left or right interior wall, near the top. Other common spots: "
    "inside the door frame, on the ceiling of the compartment, or behind the "
    "kickplate at the bottom front."
)
_DEFAULT_DISHWASHER = (
    "Open the dishwasher door and look for a sticker along the top, side, or "
    "bottom edge of the interior door frame (the part you see when the door "
    "is open). Some models have it on the left or right interior side wall."
)

LOCATIONS: dict[tuple[str, ApplianceType], str] = {
    ("whirlpool", "fridge"): (
        "On a Whirlpool refrigerator, the model number tag is usually inside "
        "the fresh-food compartment on the upper-left side wall, or along the "
        "top ceiling. On side-by-side models it's often on the right interior "
        "wall near the top."
    ),
    ("whirlpool", "dishwasher"): (
        "On a Whirlpool dishwasher, open the door and look for a silver or "
        "white sticker along the right interior side wall or on the top edge "
        "of the inner door panel."
    ),
    ("kitchenaid", "fridge"): (
        "On a KitchenAid refrigerator, the tag is typically on the left or "
        "right interior wall inside the fresh-food compartment, near the top."
    ),
    ("kitchenaid", "dishwasher"): (
        "On a KitchenAid dishwasher, open the door and check the top edge of "
        "the inner door panel, or along either interior side wall."
    ),
    ("maytag", "fridge"): (
        "On a Maytag refrigerator, look inside the fresh-food compartment for "
        "a tag on the upper-left side wall or along the ceiling."
    ),
    ("maytag", "dishwasher"): (
        "On a Maytag dishwasher, open the door and look along the top or "
        "right-side edge of the inner door panel for a sticker."
    ),
    ("ge", "fridge"): (
        "On a GE refrigerator, the model/serial tag is commonly inside the "
        "fresh-food compartment on the upper-left or upper-right side wall, "
        "or on the ceiling near the front."
    ),
    ("ge", "dishwasher"): (
        "On a GE dishwasher, open the door — the tag is typically along the "
        "top edge of the tub opening, or on the side of the inner door."
    ),
    ("frigidaire", "fridge"): (
        "On a Frigidaire refrigerator, look on the left-side interior wall "
        "inside the fresh-food compartment, or on the upper interior frame."
    ),
    ("frigidaire", "dishwasher"): (
        "On a Frigidaire dishwasher, open the door and look along the top or "
        "side edge of the inner door."
    ),
    ("lg", "fridge"): (
        "On an LG refrigerator, the tag is usually on the left or right "
        "interior side wall of the fresh-food compartment, near the top."
    ),
    ("lg", "dishwasher"): (
        "On an LG dishwasher, open the door and look at the top edge of the "
        "inner door or along either interior side wall."
    ),
    ("samsung", "fridge"): (
        "On a Samsung refrigerator, look inside the fresh-food compartment "
        "on the left or right interior wall — often near the top or on the "
        "ceiling toward the front."
    ),
    ("samsung", "dishwasher"): (
        "On a Samsung dishwasher, open the door and check the top edge of "
        "the inner door panel for the model/serial sticker."
    ),
    ("bosch", "dishwasher"): (
        "On a Bosch dishwasher, open the door and look along the top-right "
        "or top-left edge of the inner door, or on the right interior side "
        "wall near the top."
    ),
}


def lookup(brand: str | None, appliance_type: ApplianceType) -> str:
    key = (brand.lower().strip(), appliance_type) if brand else None
    if key and key in LOCATIONS:
        return LOCATIONS[key]
    return _DEFAULT_FRIDGE if appliance_type == "fridge" else _DEFAULT_DISHWASHER


def supported_brands() -> list[str]:
    return sorted({brand for brand, _ in LOCATIONS.keys()})
