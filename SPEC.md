# PartSelect Chat Agent — Technical Spec

Architecture and stack for the take-home case study. Product scope and feature cuts are in [`PRODUCT.md`](./PRODUCT.md); quick-start and file layout are in [`README.md`](./README.md).

This document captures the design intent before the build. Where implementation diverged, the README and code are authoritative and are noted inline below.

## Problem

Design and build a domain-scoped chat agent for PartSelect, limited to **refrigerator and dishwasher** parts. The agent should provide product information and transactional assistance, and must stay in-scope — refusing unrelated queries rather than hallucinating.

## Evaluation criteria (from the brief)

- Interface design and UX
- Agentic architecture
- Extensibility and scalability
- Accuracy and efficiency of responses

## Target user queries

Three example intents from the brief. The agent must handle these well, and generalise beyond them — not treat them as special cases.

1. **Install guidance** — *"How can I install part number PS11752778?"*
2. **Compatibility lookup** — *"Is this part compatible with my WDT780SAEM1 model?"*
3. **Symptom triage** — *"The ice maker on my Whirlpool fridge is not working. How can I fix it?"*

## Stack

| Layer | Choice | Notes |
| --- | --- | --- |
| Backend | Python + FastAPI | SSE for streaming |
| Agent model | Claude Sonnet 4.6 (`claude-sonnet-4-6`) | tool use + streaming via the Anthropic SDK |
| Vector store | Chroma (local, file-backed) | zero infra |
| Embeddings | OpenAI `text-embedding-3-small` | cheap, good enough |
| Relational store | SQLite | full part blobs + compat table |
| Scraper | `curl_cffi` + BeautifulSoup | TLS impersonation bypasses the WAF — see README |
| Frontend | Next.js 16 (App Router) + Tailwind v4 | raw Tailwind, no component library |
| Brand colour | `#337778` teal | PartSelect's real `theme-color`; the initial plan of "blue/yellow" was wrong |

## Agent loop

A tool-using agent — not a monolithic prompt. Claude decides which tool(s) to call each turn, and the loop runs until the model emits a final message or the iteration cap is reached.

Planned tools at spec time:

- `search_parts(query, appliance_type)` — semantic search over the indexed corpus
- `check_compatibility(part_number, model_number)` — cross-reference the part's compat list
- `get_install_guide(part_number)` — install steps, video link, difficulty
- `diagnose_symptom(appliance_type, brand, symptom)` — map symptom → candidate parts
- `lookup_order(order_id)` — **mocked** (stretch goal, no real auth/commerce)

As built the agent exposes **8 tools** — the four above plus `get_part_details`, `find_model_number_location`, `live_fetch_part`, and `search_model_parts_live`. `lookup_order` was cut as part of the broader post-purchase de-scope (see `PRODUCT.md`). See the README for the full list and their contracts.

Scope guardrail is handled by the system prompt — no separate classifier model.

## Data strategy

Hybrid, chosen deliberately over pure real-time scraping:

- **Pre-indexed seed corpus** of popular fridge + dishwasher parts, in SQLite (full blob) + Chroma (embeddings). Fast retrieval, reliable demo.
- **Live-fetch tools** for cache misses (`live_fetch_part`, `search_model_parts_live`) — preserves the "up-to-date" story.
- **Future:** scheduled re-crawl.

**Rationale.** Building a robust real-time scraper for every request would add latency and operational complexity without improving the core product experience for the MVP. The hybrid approach keeps the assistant fast on the happy path while preserving a live fallback for misses.

## Out of scope

- Real checkout / payments.
- User auth and accounts.
- Real order history (would be mocked).
- Live re-crawl scheduler.
- Appliance categories beyond fridge and dishwasher.
