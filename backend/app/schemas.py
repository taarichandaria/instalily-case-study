"""Shared Pydantic models for the agent + scraper."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ApplianceType = Literal["fridge", "dishwasher"]
InstallDifficulty = Literal["easy", "moderate", "difficult", "unknown"]


class RelatedPart(BaseModel):
    """Compact reference used inside `you_may_also_need`."""

    ps_number: str
    name: str
    price_usd: float | None = None


class Part(BaseModel):
    """Canonical scraped part. One row per PartSelect product."""

    ps_number: str
    oem_number: str | None = None
    name: str
    brand: str | None = None
    appliance_type: ApplianceType

    price_usd: float | None = None
    in_stock: bool | None = None

    description: str = ""
    symptoms_fixed: list[str] = Field(default_factory=list)

    install_difficulty: InstallDifficulty = "unknown"
    install_time_min: int | None = None
    install_steps: list[str] = Field(default_factory=list)
    install_tools: list[str] = Field(default_factory=list)
    install_video_url: str | None = None
    safety_flags: list[str] = Field(default_factory=list)

    you_may_also_need: list[RelatedPart] = Field(default_factory=list)
    compat_models: list[str] = Field(default_factory=list)

    image_url: str | None = None
    source_url: str
    scraped_at: datetime = Field(default_factory=datetime.utcnow)


# -- Chat / tool envelopes -------------------------------------------------


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class ToolStartEvent(BaseModel):
    kind: Literal["tool_start"] = "tool_start"
    name: str
    input: dict


class ToolEndEvent(BaseModel):
    kind: Literal["tool_end"] = "tool_end"
    name: str
    ok: bool


class TextDeltaEvent(BaseModel):
    kind: Literal["text"] = "text"
    text: str


class DoneEvent(BaseModel):
    kind: Literal["done"] = "done"
