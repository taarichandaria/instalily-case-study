"""Symptom-driven part triage: biases the semantic query toward fix wording."""

from __future__ import annotations

from app.store import chroma_index


async def run(
    symptom: str,
    appliance_type: str,
    brand: str | None = None,
    model_number: str | None = None,
) -> dict:
    # Compose a query that weights the "fixes X" phrasing present in our
    # embedded documents.
    query = f"Fixes: {symptom}. Symptom on {appliance_type}."
    if brand:
        query += f" Brand: {brand}."
    results = chroma_index.search(
        query, n_results=6, appliance_type=appliance_type, brand=brand
    )
    return {
        "symptom": symptom,
        "appliance_type": appliance_type,
        "brand": brand,
        "model_number": model_number,
        "candidates": results,
    }


SCHEMA = {
    "name": "diagnose_symptom",
    "description": (
        "Given a user-reported symptom (e.g. 'ice maker not making ice', "
        "'dishwasher not draining'), return ranked candidate parts that "
        "commonly fix it. Requires the appliance type. Pass brand and "
        "model_number when known — they're not used to filter here, but are "
        "echoed back so downstream compatibility checks have context."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "symptom": {
                "type": "string",
                "description": "Short phrase describing what's wrong.",
            },
            "appliance_type": {
                "type": "string",
                "enum": ["fridge", "dishwasher"],
            },
            "brand": {"type": "string", "description": "Appliance brand if known."},
            "model_number": {
                "type": "string",
                "description": "Appliance model number if known.",
            },
        },
        "required": ["symptom", "appliance_type"],
    },
}
