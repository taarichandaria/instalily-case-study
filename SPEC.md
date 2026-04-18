# PartSelect Chat Agent — Spec

Take-home case study for InstaLILY AI (SWE Intern).

Product scope and feature decisions live in `PRODUCT.md`. This doc covers architecture and stack.

## Problem

Design and build a domain-scoped chat agent for the PartSelect e-commerce site, limited to **Refrigerator and Dishwasher parts**. The agent provides product info and transactional assistance, and must stay in-scope (refuse unrelated queries).

## Evaluation criteria (from the brief)

- Interface design / UX
- Agentic architecture
- Extensibility and scalability
- Accuracy and efficiency of responses

## Target user queries

Three example intents from the brief — the agent must handle these well:

1. **Install guidance** — "How can I install part number PS11752778?"
2. **Compatibility lookup** — "Is this part compatible with my WDT780SAEM1 model?"
3. **Symptom triage / troubleshooting** — "The ice maker on my Whirlpool fridge is not working. How can I fix it?"

The agent should generalize beyond these, not just handle them as special cases.

## Architecture

### Stack

- **Backend:** Python + FastAPI
- **Agent model:** Claude Sonnet 4.6 (`claude-sonnet-4-6`) via the Anthropic SDK — tool use, streaming
- **Vector store:** Chroma (local, file-backed — zero infra)
- **Embeddings:** OpenAI `text-embedding-3-small` (cheap, good enough)
- **Frontend:** Next.js (App Router) + Tailwind + shadcn/ui
- **Branding:** align with PartSelect's blue/yellow palette

### Agent loop

Tool-using agent (not a monolithic prompt). Claude decides which tool(s) to call per turn.

Planned tools:

- `search_parts(query, appliance_type)` — semantic search over the indexed corpus
- `check_compatibility(part_number, model_number)` — cross-reference part's compat list
- `get_install_guide(part_number)` — return install steps / video link / difficulty
- `diagnose_symptom(appliance_type, brand, symptom)` — map symptom → candidate parts
- `lookup_order(order_id)` — **mocked** with realistic payload (no real auth/commerce)

Scope guardrail: system prompt + a refusal path for out-of-scope queries (no separate classifier model needed).

### Data strategy

Hybrid, chosen deliberately over pure real-time scraping:

- **Pre-indexed seed corpus** (~200–500 popular fridge + dishwasher parts) — fast retrieval, reliable demo
- **Live-fetch tool** for cache misses — preserves the "up to date" story
- Future: scheduled re-crawl

Rationale: building a robust real-time scraper for every request would add latency and operational complexity without improving the core product experience for the MVP. A hybrid approach keeps the assistant fast while preserving a live fallback path for misses.

## Out of scope

- Real checkout / payments
- User auth / accounts
- Real order history (mocked)
- Live re-crawl scheduler
- Categories beyond fridge + dishwasher
