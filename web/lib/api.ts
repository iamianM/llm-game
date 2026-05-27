import { requirePersisted, sessionStore } from "./storage";
import type {
  AvailableAction,
  CastDetail,
  CheckpointListResponse,
  CheckpointSummary,
  Gender,
  NewSessionEnvelope,
  SessionResponse,
  TurnResponse,
  TurnResponseEnvelope
} from "./types";

// On Vercel, `vercel.json` routes /api/* to the FastAPI service and strips the
// `/api` prefix before invoking the function — so the backend's routes are
// defined at root (`/session/new`), and the browser reaches them via `/api/*`.
// Locally, the FastAPI dev server is reached at `http://127.0.0.1:8000/...`
// without any prefix.
const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ??
  (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000" : "/api");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
      cache: "no-store"
    });
  } catch {
    throw new Error(
      `Cannot reach the Paradise Hearts API at ${API_BASE || "this origin"}. Start or restart the FastAPI server, then try again.`
    );
  }
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  return (await response.json()) as T;
}

async function errorMessage(response: Response): Promise<string> {
  const body = await response.text();
  if (!body) return response.statusText;
  try {
    const parsed = JSON.parse(body) as {
      detail?: { error?: { message?: string } };
      error?: { message?: string };
    };
    return parsed.detail?.error?.message ?? parsed.error?.message ?? body;
  } catch {
    return body;
  }
}

export async function newSession(archetype: string, gender: Gender, mockLlm: boolean): Promise<SessionResponse> {
  const envelope = await request<NewSessionEnvelope>("/session/new", {
    method: "POST",
    body: JSON.stringify({ archetype, player_gender: gender, seed: 42, mock_llm: mockLlm })
  });
  sessionStore.save(envelope.persisted);
  return envelope.view;
}

export async function listCheckpoints(): Promise<CheckpointSummary[]> {
  const data = await request<CheckpointListResponse>("/checkpoints");
  return data.checkpoints;
}

export async function sessionFromCheckpoint(name: string, mockLlm: boolean): Promise<SessionResponse> {
  const envelope = await request<NewSessionEnvelope>("/session/from-checkpoint", {
    method: "POST",
    body: JSON.stringify({ name, mock_llm: mockLlm })
  });
  sessionStore.save(envelope.persisted);
  return envelope.view;
}

export function getSession(sessionId: string): Promise<SessionResponse> {
  const persisted = requirePersisted(sessionId);
  return request<SessionResponse>("/session/view", {
    method: "POST",
    body: JSON.stringify(persisted)
  });
}

export async function submitTurn(sessionId: string, action: AvailableAction): Promise<TurnResponse> {
  const persisted = requirePersisted(sessionId);
  const envelope = await request<TurnResponseEnvelope>("/session/turn", {
    method: "POST",
    body: JSON.stringify({ persisted, action })
  });
  sessionStore.save(envelope.persisted);
  return envelope.view;
}

type StreamHandlers = {
  onDialogueStart?: (speakerName: string) => void;
  onDialogueChunk?: (text: string) => void;
};

export async function submitTurnStream(
  sessionId: string,
  action: AvailableAction,
  handlers: StreamHandlers = {}
): Promise<TurnResponse> {
  // The SSE endpoint can fail at the TLS/proxy layer (e.g.
  // ERR_SSL_BAD_RECORD_MAC_ALERT on some Vercel edges, function timeouts).
  // We try the stream first for the typewriter feel and fall back to the
  // non-streaming turn endpoint on any failure so gameplay is uninterrupted.
  try {
    return await streamTurn(sessionId, action, handlers);
  } catch (err) {
    if (typeof console !== "undefined") {
      console.warn("Streaming turn failed, falling back to non-streaming:", err);
    }
    return await submitTurn(sessionId, action);
  }
}

async function streamTurn(
  sessionId: string,
  action: AvailableAction,
  handlers: StreamHandlers
): Promise<TurnResponse> {
  const persisted = requirePersisted(sessionId);
  const response = await fetch(`${API_BASE}/session/turn/stream`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ persisted, action }),
    cache: "no-store"
  });
  if (!response.ok || !response.body) {
    const body = await response.text();
    throw new Error(body || response.statusText);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let envelope: TurnResponseEnvelope | null = null;
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const parsed = parseSseFrame(frame);
      if (!parsed) continue;
      if (parsed.event === "error") throw new Error(String(parsed.data?.message ?? "stream failed"));
      if (parsed.event === "dialogue_start")
        handlers.onDialogueStart?.(String(parsed.data?.speaker_name ?? "Producer"));
      if (parsed.event === "dialogue_chunk") handlers.onDialogueChunk?.(String(parsed.data?.text ?? ""));
      if (parsed.event === "response") envelope = parsed.data as unknown as TurnResponseEnvelope;
    }
    if (done) break;
  }
  if (!envelope) throw new Error("stream ended without a turn response");
  sessionStore.save(envelope.persisted);
  return envelope.view;
}

function parseSseFrame(frame: string): { event: string; data: Record<string, unknown> | null } | null {
  const event = frame.match(/^event:\s*(.+)$/m)?.[1]?.trim();
  const data = frame.match(/^data:\s*(.+)$/m)?.[1]?.trim();
  if (!event || !data) return null;
  return { event, data: JSON.parse(data) as Record<string, unknown> };
}

export function getCast(sessionId: string, npcId: string): Promise<CastDetail> {
  const persisted = requirePersisted(sessionId);
  return request<CastDetail>("/session/cast", {
    method: "POST",
    body: JSON.stringify({ persisted, npc_id: npcId })
  });
}
