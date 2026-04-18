export type Role = "user" | "assistant";

export interface ToolActivity {
  id: string;
  name: string;
  status: "running" | "ok" | "error";
}

export interface PartPreview {
  ps_number: string;
  name: string;
  image_url: string;
  price_usd: number | null;
  source_url: string | null;
}

export interface Message {
  id: string;
  role: Role;
  content: string;
  tools: ToolActivity[];
  parts: PartPreview[];
  streaming?: boolean;
}

export interface ChatThread {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  updatedAt: number;
}

export type StreamEvent =
  | { kind: "text"; text: string }
  | { kind: "tool_start"; name: string; input: Record<string, unknown> }
  | { kind: "tool_end"; name: string; ok: boolean }
  | { kind: "part_previews"; parts: PartPreview[] }
  | { kind: "done" }
  | { kind: "error"; message: string };
