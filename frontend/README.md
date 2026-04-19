# Frontend

Next.js 16 (App Router) chat UI for the PartSelect agent. See the [root README](../README.md) for architecture and setup.

## Dev

```bash
npm install
npm run dev         # http://localhost:3000, proxies /api/chat → backend :8000
npx tsc --noEmit    # typecheck
```

The backend must be running at `http://localhost:8000` — `app/api/chat/route.ts` is a raw SSE pass-through proxy.

## Layout

```
app/
  page.tsx              Chat page (server component shell)
  api/chat/route.ts     SSE proxy → backend /chat
components/
  Chat.tsx              Main chat UI (client)
  Message.tsx           Message bubble + streaming cursor
  PartSectionMedia.tsx  Inline part preview cards
  ToolBadge.tsx         Tool-activity chips
  SuggestedPrompts.tsx  Empty-state prompt chips
lib/
  sse.ts                SSE stream parser
  formatAssistantContent.ts
  types.ts              Shared types
```

Brand colour is `#337778` (PartSelect's real `theme-color`), used via Tailwind. No component library — plain Tailwind v4.
