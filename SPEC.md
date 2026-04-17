# PartSelect Chat Agent — Spec

Take-home case study for InstaLILY AI (SWE Intern).
Deadline: 48 hours from 2026-04-17.

Product scope and feature decisions live in `PRODUCT.md`. This doc covers architecture, stack, and the build plan.

## Problem

Design and build a domain-scoped chat agent for the PartSelect e-commerce site, limited to **Refrigerator and Dishwasher parts**. The agent provides product info and transactional assistance, and must stay in-scope (refuse unrelated queries).

Deliverables: source code + Loom walkthrough. Slide deck optional.

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

Scope guardrail: system prompt + a refusal path for out-of-scope queries (no classifier model — overkill at this timeline).

### Data strategy

Hybrid, chosen deliberately over pure real-time scraping:

- **Pre-indexed seed corpus** (~200–500 popular fridge + dishwasher parts) — fast retrieval, reliable demo
- **Live-fetch tool** for cache misses — preserves the "up to date" story
- Future: scheduled re-crawl (not built in 48hrs; called out on Loom as the obvious extension)

Rationale: building a robust real-time scraper in 48hrs would starve the agent + UI of polish time. Hybrid is honest and defensible.

## Out of scope

- Real checkout / payments
- User auth / accounts
- Real order history (mocked)
- Live re-crawl scheduler
- Categories beyond fridge + dishwasher

## 48-hour build plan

| Hours | Work |
|-------|------|
| 0–8   | Scraper + seed corpus + chunking/embedding → Chroma |
| 8–20  | FastAPI agent loop with ~4 tools + scope guardrail |
| 20–36 | Next.js chat UI: streaming, product cards, branding |
| 36–44 | Polish: three demo queries perfect, edge cases, mocked order lookup |
| 44–48 | Loom recording + README |

## Loom talking points

- Why hybrid data (pre-index + live fetch) over pure real-time
- Why tool use over a single prompt — extensibility story (adding a new tool = adding a capability)
- How the scope guardrail works and where it would break
- What would change if this were production (scheduled re-crawl, pgvector, observability, eval harness)
