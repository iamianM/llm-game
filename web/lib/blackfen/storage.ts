import type { BlackfenPersistedSession } from "./types";

const PREFIX = "blackfen.session.";
const CURRENT = "blackfen.currentSessionId";

export const blackfenSessionStore = {
  save(session: BlackfenPersistedSession): void {
    localStorage.setItem(`${PREFIX}${session.session_id}`, JSON.stringify(session));
    localStorage.setItem(CURRENT, session.session_id);
  },
  load(sessionId: string): BlackfenPersistedSession | null {
    const raw = localStorage.getItem(`${PREFIX}${sessionId}`);
    return raw ? (JSON.parse(raw) as BlackfenPersistedSession) : null;
  },
  current(): string | null {
    return localStorage.getItem(CURRENT);
  }
};

export function requireBlackfenPersisted(sessionId: string): BlackfenPersistedSession {
  const persisted = blackfenSessionStore.load(sessionId);
  if (!persisted) throw new Error("Blackfen session not found. Start a new run.");
  return persisted;
}
