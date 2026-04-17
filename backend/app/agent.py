"""Claude tool-use loop, streaming SSE events for the FastAPI endpoint.

Events yielded (each is a dict — main.py wraps them into SSE frames):
    {"kind": "text", "text": "..."}          text delta from the model
    {"kind": "tool_start", "name": ..., "input": {...}}
    {"kind": "tool_end",   "name": ..., "ok": bool}
    {"kind": "done"}
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import AsyncIterator, Iterable

from anthropic import AsyncAnthropic

from app.prompts import SYSTEM_PROMPT
from app.schemas import ChatMessage
from app.tools import registry

log = logging.getLogger(__name__)

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
MAX_TOKENS = 2048
MAX_ITERATIONS = 8

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        _client = AsyncAnthropic(api_key=api_key)
    return _client


def _to_anthropic_messages(history: Iterable[ChatMessage]) -> list[dict]:
    return [{"role": m.role, "content": m.content} for m in history]


async def _run_tool(name: str, args: dict) -> dict:
    return await registry.dispatch(name, args)


async def stream_reply(history: list[ChatMessage]) -> AsyncIterator[dict]:
    """Drive the tool-use loop and yield streaming events."""
    client = _get_client()
    messages = _to_anthropic_messages(history)
    tools = registry.tool_schemas()

    for iteration in range(MAX_ITERATIONS):
        pending_tool_uses: list[dict] = []  # {id, name, input}
        assistant_content: list[dict] = []  # mirror of the response for history

        async with client.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        ) as stream:
            async for event in stream:
                et = event.type
                if et == "content_block_start":
                    block = event.content_block
                    if block.type == "tool_use":
                        pending_tool_uses.append(
                            {"id": block.id, "name": block.name, "input": {}}
                        )
                        yield {
                            "kind": "tool_start",
                            "name": block.name,
                            "input": {},
                        }
                elif et == "text":
                    yield {"kind": "text", "text": event.text}
                # input_json streaming is handled implicitly via final message

            final = await stream.get_final_message()

        # Rebuild assistant content from the final message (authoritative)
        for block in final.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append(
                    {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )

        messages.append({"role": "assistant", "content": assistant_content})

        if final.stop_reason != "tool_use":
            break

        # Execute tool calls in parallel
        tool_uses = [b for b in final.content if b.type == "tool_use"]
        log.info(
            "iter %d: executing %d tool call(s): %s",
            iteration,
            len(tool_uses),
            [b.name for b in tool_uses],
        )

        async def _exec(b) -> tuple[str, str, dict, bool]:
            try:
                result = await _run_tool(b.name, dict(b.input))
                ok = "error" not in result
            except Exception as e:  # noqa: BLE001
                result = {"error": str(e)}
                ok = False
            return b.id, b.name, result, ok

        results = await asyncio.gather(*(_exec(b) for b in tool_uses))

        tool_result_blocks: list[dict] = []
        for tool_id, name, result, ok in results:
            yield {"kind": "tool_end", "name": name, "ok": ok}
            tool_result_blocks.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": json.dumps(result, default=str),
                    "is_error": not ok,
                }
            )

        messages.append({"role": "user", "content": tool_result_blocks})

    yield {"kind": "done"}
