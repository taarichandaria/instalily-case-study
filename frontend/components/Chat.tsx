"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";
import type { Message, StreamEvent, ToolActivity } from "@/lib/types";
import { parseSSE } from "@/lib/sse";
import { Message as MessageView } from "./Message";
import { SuggestedPrompts } from "./SuggestedPrompts";

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

export function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  const send = useCallback(
    async (text: string) => {
      const userMsg: Message = {
        id: uid(),
        role: "user",
        content: text,
        tools: [],
      };
      const assistantId = uid();
      const assistantMsg: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        tools: [],
        streaming: true,
      };

      const history = [...messages, userMsg];
      setMessages([...history, assistantMsg]);
      setBusy(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            messages: history.map(({ role, content }) => ({ role, content })),
          }),
          signal: controller.signal,
        });
        if (!res.ok) {
          throw new Error(`backend ${res.status}`);
        }

        // Track tool activity IDs so we can resolve tool_end events
        const pendingByName: Record<string, string[]> = {};

        await parseSSE(res, (ev: StreamEvent) => {
          if (ev.kind === "text") {
            setMessages((ms) =>
              ms.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content + ev.text }
                  : m,
              ),
            );
          } else if (ev.kind === "tool_start") {
            const activity: ToolActivity = {
              id: uid(),
              name: ev.name,
              status: "running",
            };
            pendingByName[ev.name] = [
              ...(pendingByName[ev.name] ?? []),
              activity.id,
            ];
            setMessages((ms) =>
              ms.map((m) =>
                m.id === assistantId
                  ? { ...m, tools: [...m.tools, activity] }
                  : m,
              ),
            );
          } else if (ev.kind === "tool_end") {
            const ids = pendingByName[ev.name] ?? [];
            const activityId = ids.shift();
            pendingByName[ev.name] = ids;
            if (!activityId) return;
            setMessages((ms) =>
              ms.map((m) =>
                m.id === assistantId
                  ? {
                      ...m,
                      tools: m.tools.map((t) =>
                        t.id === activityId
                          ? { ...t, status: ev.ok ? "ok" : "error" }
                          : t,
                      ),
                    }
                  : m,
              ),
            );
          } else if (ev.kind === "error") {
            setMessages((ms) =>
              ms.map((m) =>
                m.id === assistantId
                  ? {
                      ...m,
                      content:
                        m.content +
                        `\n\n_Sorry — something went wrong (${ev.message}). Please try again._`,
                    }
                  : m,
              ),
            );
          }
        });
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setMessages((ms) =>
            ms.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    content:
                      m.content +
                      `\n\n_Connection to the assistant failed. Is the backend running?_`,
                  }
                : m,
            ),
          );
        }
      } finally {
        setMessages((ms) =>
          ms.map((m) =>
            m.id === assistantId ? { ...m, streaming: false } : m,
          ),
        );
        setBusy(false);
        abortRef.current = null;
      }
    },
    [messages],
  );

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || busy) return;
    setInput("");
    send(trimmed);
  };

  return (
    <div className="flex flex-col h-[100dvh] bg-[color:var(--background)]">
      <header className="border-b border-[color:var(--border)] bg-white px-4 py-3 flex items-center gap-2 shadow-sm">
        <div className="h-7 w-7 rounded-md bg-[color:var(--ps-teal)] flex items-center justify-center">
          <span className="text-white font-bold text-sm">PS</span>
        </div>
        <div className="flex-1">
          <div className="text-sm font-semibold text-[color:var(--foreground)]">
            PartSelect Assistant
          </div>
          <div className="text-[11px] text-zinc-500">
            Refrigerator &amp; dishwasher parts
          </div>
        </div>
      </header>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto"
      >
        <div className="max-w-3xl mx-auto px-4 py-4">
          {messages.length === 0 ? (
            <SuggestedPrompts onPick={(p) => send(p)} />
          ) : (
            <div className="flex flex-col gap-4">
              {messages.map((m) => (
                <MessageView key={m.id} message={m} />
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-[color:var(--border)] bg-white">
        <form
          onSubmit={onSubmit}
          className="max-w-3xl mx-auto px-4 py-3 flex gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about a part, model, or symptom…"
            disabled={busy}
            className="flex-1 rounded-full border border-[color:var(--border)] px-4 py-2.5 text-[15px] outline-none focus:border-[color:var(--ps-teal)] focus:ring-2 focus:ring-[color:var(--ps-teal)]/20 bg-white disabled:bg-zinc-50"
          />
          <button
            type="submit"
            disabled={busy || !input.trim()}
            aria-label="Send"
            className="rounded-full bg-[color:var(--ps-teal)] hover:bg-[color:var(--ps-teal-dark)] disabled:bg-zinc-300 text-white px-4 py-2.5 flex items-center gap-2 text-sm font-medium transition-colors"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
