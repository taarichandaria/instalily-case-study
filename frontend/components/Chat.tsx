"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Plus, Send } from "lucide-react";
import type {
  Message,
  PartPreview,
  StreamEvent,
  ToolActivity,
} from "@/lib/types";
import { parseSSE } from "@/lib/sse";
import { Message as MessageView } from "./Message";
import { SuggestedPrompts } from "./SuggestedPrompts";

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

function mergePartPreviews(existing: PartPreview[], incoming: PartPreview[]) {
  if (incoming.length === 0) return existing;

  const merged = [...existing];
  const indexByPs = new Map(
    merged.map((part, index) => [part.ps_number, index] as const),
  );

  for (const part of incoming) {
    const index = indexByPs.get(part.ps_number);
    if (index == null) {
      indexByPs.set(part.ps_number, merged.length);
      merged.push(part);
      continue;
    }
    merged[index] = { ...merged[index], ...part };
  }

  return merged;
}

export function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const messagesRef = useRef<Message[]>([]);
  const requestTokenRef = useRef(0);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const startNewChat = useCallback(() => {
    requestTokenRef.current += 1;
    abortRef.current?.abort();
    abortRef.current = null;
    setBusy(false);
    setInput("");
    setMessages([]);
  }, []);

  const send = useCallback(
    async (text: string) => {
      if (busy) return;

      const token = requestTokenRef.current + 1;
      requestTokenRef.current = token;

      const userMsg: Message = {
        id: uid(),
        role: "user",
        content: text,
        tools: [],
        parts: [],
      };
      const assistantId = uid();
      const assistantMsg: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        tools: [],
        parts: [],
        streaming: true,
      };

      const history = [...messagesRef.current, userMsg];
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

        const pendingByName: Record<string, string[]> = {};

        await parseSSE(res, (ev: StreamEvent) => {
          if (requestTokenRef.current !== token) {
            return;
          }

          if (ev.kind === "text") {
            setMessages((currentMessages) =>
              currentMessages.map((message) =>
                message.id === assistantId
                  ? { ...message, content: message.content + ev.text }
                  : message,
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
            setMessages((currentMessages) =>
              currentMessages.map((message) =>
                message.id === assistantId
                  ? { ...message, tools: [...message.tools, activity] }
                  : message,
              ),
            );
          } else if (ev.kind === "tool_end") {
            const ids = pendingByName[ev.name] ?? [];
            const activityId = ids.shift();
            pendingByName[ev.name] = ids;
            if (!activityId) return;
            setMessages((currentMessages) =>
              currentMessages.map((message) =>
                message.id === assistantId
                  ? {
                      ...message,
                      tools: message.tools.map((tool) =>
                        tool.id === activityId
                          ? { ...tool, status: ev.ok ? "ok" : "error" }
                          : tool,
                      ),
                    }
                  : message,
              ),
            );
          } else if (ev.kind === "part_previews") {
            setMessages((currentMessages) =>
              currentMessages.map((message) =>
                message.id === assistantId
                  ? {
                      ...message,
                      parts: mergePartPreviews(message.parts, ev.parts),
                    }
                  : message,
              ),
            );
          } else if (ev.kind === "error") {
            setMessages((currentMessages) =>
              currentMessages.map((message) =>
                message.id === assistantId
                  ? {
                      ...message,
                      content:
                        message.content +
                        `\n\n_Sorry — something went wrong (${ev.message}). Please try again._`,
                    }
                  : message,
              ),
            );
          }
        });
      } catch (err) {
        if (
          (err as Error).name !== "AbortError" &&
          requestTokenRef.current === token
        ) {
          setMessages((currentMessages) =>
            currentMessages.map((message) =>
              message.id === assistantId
                ? {
                    ...message,
                    content:
                      message.content +
                      `\n\n_Connection to the assistant failed. Is the backend running?_`,
                  }
                : message,
            ),
          );
        }
      } finally {
        if (requestTokenRef.current === token) {
          setMessages((currentMessages) =>
            currentMessages.map((message) =>
              message.id === assistantId
                ? { ...message, streaming: false }
                : message,
            ),
          );
          setBusy(false);
          abortRef.current = null;
        }
      }
    },
    [busy],
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
      <header className="border-b border-[color:var(--border)] bg-[color:var(--ps-teal)] px-4 py-3 shadow-sm">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-none bg-[color:var(--ps-orange-dark)]">
            <span className="text-sm font-bold text-white">PS</span>
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-sm font-bold text-white">
              PartSelect Assistant
            </div>
            <div className="text-[11px] text-white/70">
              Refrigerator &amp; dishwasher parts
            </div>
          </div>
          <button
            type="button"
            onClick={startNewChat}
            className="inline-flex items-center gap-1.5 rounded-none border border-white/20 bg-white/10 px-3 py-2 text-xs font-bold text-white transition-colors hover:bg-white/16"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>New chat</span>
          </button>
        </div>
      </header>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto"
      >
        <div className="mx-auto max-w-3xl px-4 py-4">
          {messages.length === 0 ? (
            <SuggestedPrompts
              onPick={(prompt) => send(prompt)}
              disabled={busy}
            />
          ) : (
            <div className="flex flex-col gap-4">
              {messages.map((message) => (
                <MessageView
                  key={message.id}
                  message={message}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-[color:var(--border)] bg-white">
        <form
          onSubmit={onSubmit}
          className="mx-auto max-w-3xl px-4 py-3 flex gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about a part, model, or symptom…"
            disabled={busy}
            className="flex-1 rounded-none border border-[color:var(--border)] px-4 py-2.5 text-[15px] outline-none focus:border-[color:var(--ps-teal)] focus:ring-2 focus:ring-[color:var(--ps-teal)]/20 bg-white disabled:bg-zinc-50"
          />
          <button
            type="submit"
            disabled={busy || !input.trim()}
            aria-label="Send"
            className="rounded-none bg-[color:var(--ps-yellow)] hover:bg-[color:var(--ps-yellow-dark)] disabled:bg-zinc-300 disabled:text-zinc-500 text-zinc-900 px-5 py-2.5 flex items-center gap-2 text-sm font-bold transition-colors"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
