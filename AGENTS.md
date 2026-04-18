# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project

Take-home case study for InstaLILY AI. A domain-scoped chat agent for PartSelect's **refrigerator and dishwasher** parts. Scope is locked in `PRODUCT.md`; architecture intent is in `SPEC.md`. The MVP must handle three flagship queries + one chained flow on Loom:

1. Install guidance for a specific PS number (e.g. `PS11752778`).
2. Compatibility check: PS number × model number (e.g. `WDT780SAEM1`).
3. Symptom triage (e.g. "ice maker not making ice on a Whirlpool fridge") → candidate parts → compat → install, across one conversation without re-asking for the model.

## Commands

```bash
# Backend (cd backend)
uv sync                                     # install deps
uv run uvicorn app.main:app --reload        # API on :8000
uv run python scripts/run_scrape.py         # full scrape + embed + upsert
uv run python scripts/run_scrape.py --skip-vectors     # no OpenAI calls
uv run python scripts/run_scrape.py --reset            # clear Chroma first
uv run python scripts/run_scrape.py --limit 30         # small-batch
uv run python scripts/eval.py               # tool-layer smoke tests
uv run python scripts/eval.py --agent       # + full agent loop end-to-end

# Frontend (cd frontend)
npm install
npm run dev                                 # :3000, proxies /api/chat → backend
npx tsc --noEmit                            # typecheck
```

API keys go in `backend/.env` (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`). The scraper does not need keys when run with `--skip-vectors`; the agent loop and embedding require both.

## Architecture at a glance

```
Next.js chat UI ── /api/chat proxy ─▶ FastAPI /chat (SSE)
                                        └─▶ agent.py (Codex Sonnet 4.6 tool loop)
                                              └─▶ 7 tools in app/tools/*
                                                     ├── Chroma (semantic search)
                                                     ├── SQLite (parts + compat)
                                                     └── scraper/ (curl_cffi live fetch)
```

### Data layer — non-obvious decisions

- **SQLite holds the full `Part` blob** (`parts.blob` column, JSON-encoded Pydantic dump). Chroma only stores the composite document string + thin metadata. The `get_part_details` / `get_install_guide` tools hit SQLite, not Chroma.
- **`compat` is a separate SQLite table** indexed both ways `(ps_number, model_number)`. Compat lists can be thousands of rows per part — they're **never** sent to the LLM. `check_compatibility` returns a boolean + the total known-model count so the agent can frame confidence.
- **Chroma's `_document_text`** (`app/store/chroma_index.py`) composes `name + appliance + brand + description + "Fixes: <symptoms>" + OEM`. The "Fixes:" string is intentional — `diagnose_symptom` prepends the same phrase to the query to bias the embedding toward symptom-matching documents.

### Scraper — non-obvious decisions

- **Use `curl_cffi.requests.AsyncSession(impersonate="chrome")`.** PartSelect's edge WAF TLS-fingerprints; `httpx` / `requests` / `aiohttp` get 403 regardless of headers. See `memory/feedback_partselect_scraping.md`.
- **Part URLs require the full slug.** Bare `/PSxxx.htm` returns HTTP 500 — PartSelect demands `/PS11752778-Whirlpool-WPW10321304-Refrigerator-Door-Shelf-Bin.htm`. Seeds carry the slug (`ANCHOR_PART_SLUGS`); model pages' `<a href>` attributes surface slugs for discovered parts. `parse_model_parts_page` returns `dict[str, str]` (PS → slug path).
- **Section content is the anchor's next sibling, not inside it.** Pages like `#ProductDescription`, `#Troubleshooting`, `#InstallationInstructions`, `#RelatedParts`, `#ModelCrossReference`, `#PartVideos` are empty anchor divs — real content lives in the adjacent sibling. `_section_content(soup, id)` encodes this.
- **`_text_after_label` must not escalate past `parent`.** Walking to `parent.parent` catches outer page chrome and returns garbage (e.g. "Refrigerator" for the brand).
- **Install steps come from crowd-sourced repair stories**, not official docs. `.repair-story__title` + `.repair-story__instruction`. Trim on `Other Parts Used` to drop nested sections. Always surface `source_url` alongside these — they're customer write-ups.
- **Page-structure landmarks** (selectors that are easy to get wrong):
  - Price: prefer `.pd__price` (has `$`), fall back to `.js-partPrice` (bare number).
  - Repair rating: `[class*="pd__repair-rating__container"]` (attribute-contains selector — the class family has suffix variants).
  - YouTube video: `data-yt-init` attribute inside `#PartVideos`' next sibling.

### Agent loop — shape

- **Single model**: `Codex-sonnet-4-6`, streaming via `client.messages.stream(...)` context manager.
- **Loop cap**: 8 iterations. On `stop_reason == "tool_use"`, tools are executed in parallel via `asyncio.gather`, results appended as `tool_result` blocks, loop continues.
- **Events yielded to SSE**: `text` (deltas), `tool_start` (name + empty input — streaming tool input is skipped; the final message has it), `tool_end` (name + ok), `done`. Errors surface as an `error` event.
- **Full-history mode**: no server-side session. Each request sends the full conversation. Refreshing the frontend resets state — acceptable for this demo.

## Frontend

- **Next.js 16** with the App Router. `frontend/AGENTS.md` warns it has breaking changes vs training data; check `node_modules/next/dist/docs/` before writing new APIs.
- `app/api/chat/route.ts` proxies directly to the backend `/chat` SSE — this is a raw stream pass-through, not a `ReadableStream` transform.
- `components/Chat.tsx` is the only stateful component. Tool activity is tracked per assistant message via `pendingByName` — tool_end events resolve the oldest pending activity of that name (FIFO). There's no tool_use_id in the events; if we need per-tool correlation later, plumb the id through from the backend.
- **Brand color**: `#337778` teal (PartSelect's real `theme-color`). Not blue/yellow — that was a mistaken assumption early on.

## Adding a tool

1. Create `backend/app/tools/my_tool.py` with `SCHEMA: dict` (Anthropic tool format) + `async def run(**kwargs) -> dict`.
2. Import + register in `app/tools/registry.py`'s `_TOOLS` list.
3. Mention it in `app/prompts.py` so the model knows when to reach for it.
4. Add a case to `scripts/eval.py` if it's load-bearing for the flagship queries.

No other wiring is required — the registry drives `/chat` and the frontend.

## Out of scope / graceful refusals

Order tracking, returns/warranty, shipping ETAs, image identification, maintenance tips, checkout, auth, and non-fridge/non-dishwasher appliances are all intentionally cut (`PRODUCT.md`). The system prompt handles these with a one-sentence redirect — don't add a classifier or per-intent router.
