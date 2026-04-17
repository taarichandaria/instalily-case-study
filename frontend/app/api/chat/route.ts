export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(request: Request): Promise<Response> {
  const body = await request.text();

  const upstream = await fetch(`${BACKEND_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body,
  });

  if (!upstream.ok || !upstream.body) {
    return new Response(
      `data: ${JSON.stringify({ kind: "error", message: `backend ${upstream.status}` })}\n\n`,
      {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      },
    );
  }

  return new Response(upstream.body, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
