"""Tool registry — JSONSchemas (Anthropic tool_use format) + dispatch table.

Adding a tool: drop a module in `app/tools/` exposing `SCHEMA` + `async def
run(**kwargs)`, then add it to `_TOOLS` below.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from app.tools import (
    check_compatibility,
    diagnose_symptom,
    find_model_number_location,
    get_install_guide,
    get_part_details,
    live_fetch_part,
    search_parts,
)

log = logging.getLogger(__name__)

ToolFn = Callable[..., Awaitable[dict]]

_TOOLS: list[tuple[dict, ToolFn]] = [
    (search_parts.SCHEMA, search_parts.run),
    (diagnose_symptom.SCHEMA, diagnose_symptom.run),
    (check_compatibility.SCHEMA, check_compatibility.run),
    (get_part_details.SCHEMA, get_part_details.run),
    (get_install_guide.SCHEMA, get_install_guide.run),
    (find_model_number_location.SCHEMA, find_model_number_location.run),
    (live_fetch_part.SCHEMA, live_fetch_part.run),
]


def tool_schemas() -> list[dict]:
    return [schema for schema, _ in _TOOLS]


def tool_names() -> list[str]:
    return [schema["name"] for schema, _ in _TOOLS]


_BY_NAME: dict[str, ToolFn] = {schema["name"]: fn for schema, fn in _TOOLS}


async def dispatch(name: str, arguments: dict[str, Any]) -> dict:
    fn = _BY_NAME.get(name)
    if fn is None:
        return {"error": f"unknown tool: {name}"}
    try:
        return await fn(**arguments)
    except TypeError as e:
        log.warning("tool %s bad args %s: %s", name, arguments, e)
        return {"error": f"bad arguments for {name}: {e}"}
    except Exception as e:  # noqa: BLE001
        log.exception("tool %s raised", name)
        return {"error": f"{name} failed: {e}"}
