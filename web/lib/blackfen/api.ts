import { blackfenSessionStore, requireBlackfenPersisted } from "./storage";
import type {
  BlackfenClassId,
  BlackfenNewEnvelope,
  BlackfenSessionResponse,
  BlackfenTurnEnvelope,
  BlackfenTurnResponse
} from "./types";

function devApiBase(): string {
  if (typeof window === "undefined") return "http://127.0.0.1:8000";
  const host = window.location.hostname || "127.0.0.1";
  return `http://${host}:8000`;
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ??
  (process.env.NODE_ENV === "development" ? devApiBase() : "/api");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store"
  });
  if (!response.ok) throw new Error(await response.text());
  return (await response.json()) as T;
}

export async function newBlackfenSession(args: {
  classId: BlackfenClassId;
  playerName: string;
  seed?: number;
}): Promise<BlackfenSessionResponse> {
  const envelope = await request<BlackfenNewEnvelope>("/blackfen/session/new", {
    method: "POST",
    body: JSON.stringify({
      class_id: args.classId,
      player_name: args.playerName.trim() || "You",
      seed: args.seed ?? 42,
      mock_llm: true
    })
  });
  blackfenSessionStore.save(envelope.persisted);
  return envelope.view;
}

export async function getBlackfenSession(sessionId: string): Promise<BlackfenSessionResponse> {
  return request<BlackfenSessionResponse>("/blackfen/session/view", {
    method: "POST",
    body: JSON.stringify(requireBlackfenPersisted(sessionId))
  });
}

export async function submitBlackfenTurn(sessionId: string, text: string): Promise<BlackfenTurnResponse> {
  const envelope = await request<BlackfenTurnEnvelope>("/blackfen/session/turn", {
    method: "POST",
    body: JSON.stringify({ persisted: requireBlackfenPersisted(sessionId), action: { text } })
  });
  blackfenSessionStore.save(envelope.persisted);
  return envelope.view;
}
