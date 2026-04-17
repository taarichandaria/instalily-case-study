export type Role = "user" | "assistant";

export interface ToolActivity {
  id: string;
  name: string;
  status: "running" | "ok" | "error";
}

export interface Message {
  id: string;
  role: Role;
  content: string;
  tools: ToolActivity[];
  streaming?: boolean;
}

export type StreamEvent =
  | { kind: "text"; text: string }
  | { kind: "tool_start"; name: string; input: Record<string, unknown> }
  | { kind: "tool_end"; name: string; ok: boolean }
  | { kind: "done" }
  | { kind: "error"; message: string };
