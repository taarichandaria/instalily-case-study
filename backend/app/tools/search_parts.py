"""Semantic search over indexed parts."""

from __future__ import annotations

from app.store import chroma_index


async def run(
    query: str,
    appliance_type: str | None = None,
    brand: str | None = None,
    limit: int = 5,
) -> dict:
    results = chroma_index.search(
        query,
        n_results=min(max(limit, 1), 10),
        appliance_type=appliance_type,
        brand=brand,
    )
    return {"query": query, "results": results}


SCHEMA = {
    "name": "search_parts",
    "description": (
        "Semantic search across the indexed PartSelect catalog (refrigerator "
        "and dishwasher parts only). Use this when the user describes what "
        "they need in their own words, asks for a category of part, or is "
        "exploring options. Returns up to `limit` parts with ps_number, name, "
        "appliance_type, brand, price, and a relevance score."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Free-text description of the part or need.",
            },
            "appliance_type": {
                "type": "string",
                "enum": ["fridge", "dishwasher"],
                "description": "Restrict to one appliance. Omit if unknown.",
            },
            "brand": {
                "type": "string",
                "description": "Restrict to a brand (lowercase). Omit if unknown.",
            },
            "limit": {
                "type": "integer",
                "description": "Max number of results (1-10).",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}
