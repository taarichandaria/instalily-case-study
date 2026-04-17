"""Seed anchors for the crawl.

Strategy: a few must-include parts (for demo reliability) + a handful of
popular models whose first-page parts list we scrape. The crawl then expands
via each part's "You May Also Need" block for extra variety.
"""

from __future__ import annotations

# Must-have parts keyed by their full URL slug. Bare `/PSxxx.htm` URLs return
# 500 — PartSelect requires the canonical slug path. PS11752778 is the
# install-guidance example from the brief.
ANCHOR_PART_SLUGS: dict[str, str] = {
    "PS11752778": "/PS11752778-Whirlpool-WPW10321304-Refrigerator-Door-Shelf-Bin.htm",
}

# Popular fridge + dishwasher models. We scrape the first page of each model's
# compatible-parts list and pull those PS numbers + slugs into the crawl queue.
ANCHOR_MODELS: dict[str, str] = {
    # Dishwashers
    "WDT780SAEM1": "dishwasher",   # brief's compat example — Whirlpool dishwasher
    "KDTE334GPS0": "dishwasher",   # KitchenAid dishwasher
    # Refrigerators
    "WRS325SDHZ08": "fridge",      # Whirlpool side-by-side w/ ice maker
    "WRS325FDAM04": "fridge",      # Whirlpool side-by-side
    "MFI2570FEZ": "fridge",        # Maytag French-door
    "10640262010": "fridge",       # Kenmore (sold by Whirlpool) side-by-side
}

# Category listing pages — used as an additional seed source for popular parts.
CATEGORY_LISTING_URLS: list[str] = [
    "https://www.partselect.com/Refrigerator-Parts.htm",
    "https://www.partselect.com/Dishwasher-Parts.htm",
]
