"""Smoke tests for the three flagship queries from the brief + one chained flow.

Exercises the tool layer directly (no API key required) and, if
ANTHROPIC_API_KEY is set, runs the full agent loop end-to-end.

Usage:
    uv run python scripts/eval.py             # tool-layer tests
    uv run python scripts/eval.py --agent     # + end-to-end agent tests
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402


async def tool_tests() -> int:
    from app.tools import registry

    fails = 0

    # (1) Install query for PS11752778
    r = await registry.dispatch(
        "get_install_guide", {"ps_number": "PS11752778"}
    )
    ok = r.get("found") and r.get("install_difficulty") != "unknown" and r.get(
        "install_steps"
    )
    print(
        f"[{'PASS' if ok else 'FAIL'}] install guide PS11752778: "
        f"difficulty={r.get('install_difficulty')} steps={len(r.get('install_steps', []))}"
    )
    if not ok:
        fails += 1

    # (2) Compatibility: PS11752778 against WDT780SAEM1
    r = await registry.dispatch(
        "check_compatibility",
        {"ps_number": "PS11752778", "model_number": "WDT780SAEM1"},
    )
    ok = r["status"] in ("yes", "no") and r["total_known_models"] > 0
    print(
        f"[{'PASS' if ok else 'FAIL'}] compat PS11752778 / WDT780SAEM1: "
        f"status={r['status']} total={r['total_known_models']}"
    )
    if not ok:
        fails += 1

    # (2b) Sanity: compat against a known-good model from the compat table
    r = await registry.dispatch(
        "check_compatibility",
        {"ps_number": "PS11752778", "model_number": "10640262010"},
    )
    ok = r["status"] == "yes"
    print(
        f"[{'PASS' if ok else 'FAIL'}] compat PS11752778 / 10640262010 (known good): "
        f"status={r['status']}"
    )
    if not ok:
        fails += 1

    # (3) Symptom triage
    r = await registry.dispatch(
        "diagnose_symptom",
        {"symptom": "ice maker not making ice", "appliance_type": "fridge"},
    )
    ok = len(r.get("candidates", [])) > 0
    print(
        f"[{'PASS' if ok else 'FAIL'}] diagnose_symptom ice maker: "
        f"{len(r.get('candidates', []))} candidates"
    )
    if not ok:
        fails += 1

    # (4) Model location helper
    r = await registry.dispatch(
        "find_model_number_location",
        {"appliance_type": "fridge", "brand": "Whirlpool"},
    )
    ok = r["is_brand_specific"] and "whirlpool" in r["description"].lower()
    print(
        f"[{'PASS' if ok else 'FAIL'}] model location Whirlpool fridge: "
        f"brand_specific={r['is_brand_specific']}"
    )
    if not ok:
        fails += 1

    # (5) Scope guardrail: brand + appliance we haven't mapped
    r = await registry.dispatch(
        "find_model_number_location",
        {"appliance_type": "fridge", "brand": "Acme"},
    )
    ok = not r["is_brand_specific"] and r["description"]  # falls back cleanly
    print(
        f"[{'PASS' if ok else 'FAIL'}] model location Acme fridge (fallback): "
        f"brand_specific={r['is_brand_specific']}"
    )
    if not ok:
        fails += 1

    return fails


async def agent_tests() -> int:
    from app.agent import stream_reply
    from app.schemas import ChatMessage

    queries = [
        "How do I install part number PS11752778?",
        "Is PS11752778 compatible with my WDT780SAEM1?",
        "My Whirlpool fridge ice maker isn't making ice — what part do I need?",
    ]

    fails = 0
    for q in queries:
        history = [ChatMessage(role="user", content=q)]
        tools_called: list[str] = []
        text_parts: list[str] = []
        try:
            async for ev in stream_reply(history):
                if ev["kind"] == "tool_start":
                    tools_called.append(ev["name"])
                elif ev["kind"] == "text":
                    text_parts.append(ev["text"])
                elif ev["kind"] == "error":
                    print(f"[FAIL] agent error on '{q[:50]}...': {ev['message']}")
                    fails += 1
                    break
        except Exception as e:  # noqa: BLE001
            print(f"[FAIL] agent raised on '{q[:50]}...': {e}")
            fails += 1
            continue

        reply = "".join(text_parts)
        ok = len(tools_called) > 0 and len(reply) > 80
        print(
            f"[{'PASS' if ok else 'FAIL'}] agent: '{q[:50]}...' "
            f"tools={tools_called} reply_len={len(reply)}"
        )
        if not ok:
            fails += 1

    return fails


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", action="store_true", help="Also run agent loop")
    args = parser.parse_args()

    load_dotenv(override=True)

    print("=== tool tests ===")
    fails = await tool_tests()

    if args.agent:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("\nSkipping agent tests: ANTHROPIC_API_KEY not set")
        else:
            print("\n=== agent tests ===")
            fails += await agent_tests()

    print(f"\n{'all passed' if fails == 0 else f'{fails} failure(s)'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
