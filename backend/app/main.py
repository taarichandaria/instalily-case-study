"""FastAPI app: /chat streams agent replies as SSE, /health for sanity."""

from __future__ import annotations

import json
import logging
import os
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from app.agent import stream_reply
from app.schemas import ChatRequest
from app.store import parts_db

load_dotenv(override=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("partselect.api")

app = FastAPI(title="PartSelect Assistant")

_cors_origins = os.environ.get(
    "CORS_ORIGINS", "http://localhost:3000"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    parts_db.init_db()


@app.get("/health")
def health() -> dict:
    return {"ok": True, "parts": parts_db.total_parts()}


@app.post("/chat")
async def chat(req: ChatRequest) -> EventSourceResponse:
    async def event_stream() -> AsyncIterator[dict]:
        try:
            async for ev in stream_reply(req.messages):
                yield {"data": json.dumps(ev)}
        except Exception as e:  # noqa: BLE001
            log.exception("agent loop failed")
            yield {
                "data": json.dumps(
                    {"kind": "error", "message": f"{type(e).__name__}: {e}"}
                )
            }

    return EventSourceResponse(event_stream())
