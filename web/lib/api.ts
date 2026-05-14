import type { AvailableAction, CastDetail, Gender, SessionResponse, TurnResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store"
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || response.statusText);
  }
  return (await response.json()) as T;
}

export function newSession(archetype: string, gender: Gender, mockLlm: boolean): Promise<SessionResponse> {
  return request<SessionResponse>("/session/new", {
    method: "POST",
    body: JSON.stringify({ archetype, player_gender: gender, seed: 42, mock_llm: mockLlm })
  });
}

export function getSession(sessionId: string): Promise<SessionResponse> {
  return request<SessionResponse>(`/session/${sessionId}`);
}

export function submitTurn(sessionId: string, action: AvailableAction): Promise<TurnResponse> {
  return request<TurnResponse>(`/session/${sessionId}/turn`, {
    method: "POST",
    body: JSON.stringify(action)
  });
}

type StreamHandlers = {
  onDialogueStart?: (speakerName: string) => void;
  onDialogueChunk?: (text: string) => void;
};

export async function submitTurnStream(sessionId: string, action: AvailableAction, handlers: StreamHandlers = {}): Promise<TurnResponse> {
  const response = await fetch(`${API_BASE}/session/${sessionId}/turn/stream`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(action),
    cache: "no-store"
  });
  if (!response.ok || !response.body) {
    const body = await response.text();
    throw new Error(body || response.statusText);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: TurnResponse | null = null;
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const parsed = parseSseFrame(frame);
      if (!parsed) continue;
      if (parsed.event === "error") throw new Error(String(parsed.data?.message ?? "stream failed"));
      if (parsed.event === "dialogue_start") handlers.onDialogueStart?.(String(parsed.data?.speaker_name ?? "Producer"));
      if (parsed.event === "dialogue_chunk") handlers.onDialogueChunk?.(String(parsed.data?.text ?? ""));
      if (parsed.event === "response") result = parsed.data as TurnResponse;
    }
    if (done) break;
  }
  if (!result) throw new Error("stream ended without a turn response");
  return result;
}

function parseSseFrame(frame: string): { event: string; data: Record<string, unknown> | null } | null {
  const event = frame.match(/^event:\s*(.+)$/m)?.[1]?.trim();
  const data = frame.match(/^data:\s*(.+)$/m)?.[1]?.trim();
  if (!event || !data) return null;
  return { event, data: JSON.parse(data) as Record<string, unknown> };
}

export function getCast(sessionId: string, npcId: string): Promise<CastDetail> {
  return request<CastDetail>(`/session/${sessionId}/cast/${npcId}`);
}
