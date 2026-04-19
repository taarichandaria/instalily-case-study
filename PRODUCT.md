# PartSelect Chat Agent — Product Scope

Feature scope and explicit cuts for the take-home case study. Architecture lives in [`SPEC.md`](./SPEC.md); build details in [`README.md`](./README.md).

## Goals

A domain-scoped chat agent for the PartSelect e-commerce site, limited to **refrigerator and dishwasher** parts. It should:

- Provide accurate product information and assist with common purchase decisions.
- Stay strictly in-scope — refuse unrelated queries gracefully rather than hallucinating.
- Feel polished enough to ship, and be structured so the catalog or toolset can grow without rewrites.

The UI should align with PartSelect's branding.

## MVP feature set

### 1. Symptom triage ("something's wrong")

The user approaches with a broad issue and doesn't yet know which part they need.

- Ask clarifying questions **only when the symptom maps to >3 candidate parts, or the brand/model is unknown**. Otherwise suggest with confidence ranges rather than interrogating.
- Once the likely need is identified, offer to move into product discovery.

### 2. Product discovery

The user is ready to buy but needs help deciding between options.

- Present a short list, explaining why each fits the stated need and how they differ (price, use case, stock, install difficulty).
- Surface companion items from PartSelect's **"You May Also Need"** section on the part page — scraped, not LLM-inferred.
- Shipping ETA is zip-dependent and would be faked for the demo; see cuts below.

### 3. Compatibility

- Answer directly when the user asks "is PS_ compatible with model _?"
- Verify compatibility **before** recommending any part for purchase — no suggestion leaves the agent un-checked against the user's model.

### 4. Part identification (text-based)

- The user has a PS number or OEM number but isn't sure what it is. Given the number, return what the part is and where it fits.
- This capability should surface inside other flows too (e.g. symptom triage → "is this what I have?").

### 5. Installation guidance

- Step-by-step install instructions.
- Difficulty / time estimate (can an average person do this, or is a technician needed?). Flag this during discovery too.
- Tools required.
- Video link when available.
- Safety flags and any other follow-ups.

### 6. Model-number discovery helper

- "Where do I find the model number on my Whirlpool fridge/dishwasher?" — a first-class capability, since it's the gateway to every compatibility check.

### Cross-cutting behaviors

- **Conversation memory.** Once the user mentions a brand or model, carry it across turns — never re-ask.
- **Scope guardrail.** Refuse out-of-scope queries politely. Edge cases handled explicitly:
  - Adjacent appliances (oven, washer, dryer) → refuse, name the scope.
  - Other vendors ("can I return this to Amazon?") → refuse, redirect.
  - DIY safety beyond part replacement (rewiring, etc.) → refuse, recommend a technician.
  - Pricing negotiation or discount requests → polite redirect.
- **Graceful miss handling.** When the query is in-scope but data is missing, admit it and link out to the live PartSelect page or install video rather than hallucinating.

## Stretch (only if MVP is fully polished)

- **Order lookup** — a single mocked `lookup_order` tool with a realistic fake payload. *Not* shipping: returns, exchanges, cancel/modify, reorder, warranty — too many mocked tools with no real data to ground them.
- **Maintenance tips** — replacement cadences, seasonal checks, etc.
- **Image-based part ID** — user uploads a photo of a pulled part. Sonnet 4.6 is multimodal so this is technically reachable, but only if everything else is done.

## Out of scope (cut — Loom talking points, not in the build)

- Returns, exchanges, warranty claims, cancel / modify, reorder flows.
- Shipping-ETA math.
- Appliance categories beyond refrigerator and dishwasher.
- Real auth / checkout / payments.

## Demo success criteria

The three example queries from the brief must work flawlessly:

1. Install guide for `PS11752778`.
2. Compatibility check for model `WDT780SAEM1`.
3. Whirlpool ice-maker troubleshooting.

Plus **at least one chained flow**: symptom → diagnosis → discovery (with "You May Also Need") → compatibility → install, all in one conversation without re-asking for the model number.
