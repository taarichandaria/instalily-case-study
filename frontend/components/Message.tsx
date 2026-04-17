"use client";

import ReactMarkdown from "react-markdown";
import type { Message as MessageT } from "@/lib/types";
import { ToolBadge } from "./ToolBadge";

export function Message({ message }: { message: MessageT }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-[color:var(--ps-teal)] px-4 py-2.5 text-white text-[15px] leading-relaxed whitespace-pre-wrap">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] space-y-2">
        {message.tools.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {message.tools.map((t) => (
              <ToolBadge key={t.id} activity={t} />
            ))}
          </div>
        )}
        {(message.content.length > 0 || message.streaming) && (
          <div className="rounded-2xl rounded-bl-md bg-white border border-[color:var(--border)] px-4 py-2.5 text-[15px] text-[color:var(--foreground)] shadow-sm">
            <div
              className={`prose prose-sm max-w-none ${message.streaming && message.content.length === 0 ? "stream-cursor" : ""}`}
            >
              <ReactMarkdown
                components={{
                  a: (props) => (
                    <a
                      {...props}
                      target="_blank"
                      rel="noopener noreferrer"
                    />
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
              {message.streaming && message.content.length > 0 && (
                <span className="stream-cursor" />
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
