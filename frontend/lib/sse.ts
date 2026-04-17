import type { StreamEvent } from "./types";

/**
 * Parse an SSE stream from a fetch Response and invoke `onEvent` for each
 * data frame. Handles partial chunks that land mid-line.
 */
export async function parseSSE(
  response: Response,
  onEvent: (ev: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  if (!response.body) throw new Error("response has no body");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    if (signal?.aborted) {
      await reader.cancel();
      return;
    }
    const { value, done } = await reader.read();
    if (done) break;
    // Normalize CRLF → LF: sse_starlette emits \r\n\r\n frame separators;
    // without this, Safari's reader surfaces the bytes but indexOf("\n\n") never matches.
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      const dataLines = frame
        .split("\n")
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).trim());
      if (dataLines.length === 0) continue;
      const payload = dataLines.join("\n");
      if (!payload) continue;
      try {
        const parsed = JSON.parse(payload) as StreamEvent;
        onEvent(parsed);
      } catch {
        // swallow — malformed frames shouldn't kill the stream
      }
    }
  }
}
