# PartSelect Chat Agent

A domain-scoped chat agent for PartSelect's **refrigerator and dishwasher** parts. Take-home case study for InstaLILY AI (SWE Intern).

See [`SPEC.md`](./SPEC.md) for architecture intent and [`PRODUCT.md`](./PRODUCT.md) for feature scope and cuts.

## What it does

- **Find parts** from natural-language descriptions (semantic search over indexed PartSelect catalog).
- **Diagnose symptoms** ("ice maker not making ice") → ranked candidate parts.
- **Check compatibility** between a specific PS number and a specific appliance model.
- **Explain installation** — difficulty, time, customer-written repair steps, YouTube video, safety notes.
- **Help locate the model-number sticker** when the user doesn't know their model.
- **Fall back to live scraping** for parts outside the indexed corpus.

Streams tool activity + assistant text to the frontend via SSE — tool chips light up as the agent reasons.

## Quick start

Requires Python 3.13+ (managed via [uv](https://github.com/astral-sh/uv)) and Node 20+.

### 1. Backend

```bash
cd backend
cp .env.example .env
# Edit .env and fill in:
#   ANTHROPIC_API_KEY=sk-ant-...
#   OPENAI_API_KEY=sk-...
uv sync
```

Build the parts corpus (one-time; disk-cached so subsequent runs are free):

```bash
uv run python scripts/run_scrape.py              # full scrape + embed
# or, iteratively:
uv run python scripts/run_scrape.py --skip-vectors   # SQLite only (no API cost)
uv run python scripts/run_scrape.py --reset          # clear Chroma first
uv run python scripts/run_scrape.py --limit 30       # cap parts for testing
```

Run the API:

```bash
uv run uvicorn app.main:app --reload
```

Health check: `curl http://localhost:8000/health` → `{"ok":true,"parts":N}`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. The suggested-prompt chips cover the three flagship queries plus one chained flow.

### 3. Smoke tests

```bash
cd backend
uv run python scripts/eval.py             # tool-layer tests (no API cost)
uv run python scripts/eval.py --agent     # + full agent loop end-to-end
```

## Architecture

```
 ┌──────────────┐                ┌────────────────────────────────┐
 │ Next.js app  │ ── /api/chat ─▶│ FastAPI   /chat (SSE)          │
 │  Chat.tsx    │◀── SSE frames ─│   agent.py (tool-use loop)     │
 └──────────────┘                │     ├── Claude Sonnet 4.6      │
                                 │     └── 7 tools (registry.py)  │
                                 └────────────┬───────────────────┘
                                              │
                         ┌────────────────────┴────────────────┐
                         │                                     │
                   ┌─────▼─────┐                       ┌───────▼────────┐
                   │ Chroma    │                       │ SQLite         │
                   │ parts     │                       │ parts + compat │
                   └─────▲─────┘                       └───────▲────────┘
                         │   embeds                            │
                         │                                     │
                   ┌─────┴─────────────────────────────────────┴────┐
                   │ scraper/  (curl_cffi + BeautifulSoup, cached)  │
                   └────────────────────────────────────────────────┘
```

### Key design decisions

- **Hybrid data strategy.** A pre-scraped corpus (~70+ parts seeded from popular fridge + dishwasher models) lives in SQLite and Chroma for fast search and grounded recommendations. A `live_fetch_part` tool falls back to scraping on demand when the agent hits a gap — same parse code path, so cached-vs-live behavior is identical.
- **TLS fingerprint bypass.** PartSelect's edge WAF returns 403 to `httpx` / `requests` / `aiohttp` even with matching Chrome headers. We use [`curl_cffi`](https://github.com/yifeikong/curl_cffi) with `impersonate="chrome"` to impersonate a real browser's JA3/JA4 fingerprint.
- **Compat as a separate table.** Model compatibility lists can have thousands of rows per part. They're stored in SQLite (`compat` table), never sent wholesale to the LLM. `check_compatibility` returns a boolean + model count.
- **Scope guardrail via system prompt.** No classifier model — the system prompt enforces fridge/dishwasher-only, no order tracking, no unsafe DIY, no discounts. Tool calls ground every factual claim.
- **Extensibility.** Each tool is a single module (`app/tools/*.py`) exposing `SCHEMA` + `async def run(...)`. Drop a file, register it, done. The system prompt + registry are the two files to touch when adding a capability.

## Non-goals (for this MVP)

See `PRODUCT.md` — order tracking, returns/warranty flows, image identification, maintenance tips, and real checkout/auth are all intentionally cut. The system prompt responds gracefully to out-of-scope asks.

## File layout

```
backend/
  app/
    main.py               FastAPI app, /chat SSE endpoint
    agent.py              Claude tool-use loop
    prompts.py            System prompt
    schemas.py            Pydantic models
    scraper/              curl_cffi crawler + BeautifulSoup parser + ingest pipeline
    store/                SQLite + Chroma wrappers + static model-location dict
    tools/                One module per tool + registry.py
  scripts/
    run_scrape.py         One-shot: crawl → parse → upsert SQLite + Chroma
    eval.py               Smoke tests for the three brief queries
  data/                   SQLite + Chroma + cached raw HTML (gitignored except schema)
frontend/
  app/
    page.tsx              Chat page
    api/chat/route.ts     SSE proxy → backend
  components/
    Chat.tsx              Main chat UI (client)
    Message.tsx           Message bubble + streaming cursor
    ToolBadge.tsx         Inline tool-activity chips
    SuggestedPrompts.tsx  Empty-state prompt chips
  lib/
    sse.ts                SSE stream parser
    types.ts              Shared types
```
