// Client-side session persistence.
//
// The API is stateless: the full PersistedSession blob round-trips on every
// call. The browser owns persistence today (localStorage). When accounts ship,
// a ServerStore implementation will sync the same shape to Postgres without
// touching the call sites.

import type { PersistedSession } from "./types";

const STORAGE_PREFIX = "paradise.session.";
const CURRENT_SESSION_KEY = "paradise.currentSessionId";
const SUPPORTED_SCHEMA_VERSION = 1;

export interface SessionStore {
  load(sessionId: string): PersistedSession | null;
  save(persisted: PersistedSession): void;
  clear(sessionId: string): void;
  list(): string[];
}

class LocalStorageStore implements SessionStore {
  load(sessionId: string): PersistedSession | null {
    if (typeof window === "undefined") return null;
    const raw = window.localStorage.getItem(STORAGE_PREFIX + sessionId);
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw) as PersistedSession;
      if (parsed.schema_version !== SUPPORTED_SCHEMA_VERSION) {
        window.localStorage.removeItem(STORAGE_PREFIX + sessionId);
        return null;
      }
      return parsed;
    } catch {
      window.localStorage.removeItem(STORAGE_PREFIX + sessionId);
      return null;
    }
  }

  save(persisted: PersistedSession): void {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(STORAGE_PREFIX + persisted.session_id, JSON.stringify(persisted));
  }

  clear(sessionId: string): void {
    if (typeof window === "undefined") return;
    window.localStorage.removeItem(STORAGE_PREFIX + sessionId);
  }

  list(): string[] {
    if (typeof window === "undefined") return [];
    const ids: string[] = [];
    for (let i = 0; i < window.localStorage.length; i++) {
      const key = window.localStorage.key(i);
      if (key && key.startsWith(STORAGE_PREFIX)) ids.push(key.slice(STORAGE_PREFIX.length));
    }
    return ids;
  }
}

export const sessionStore: SessionStore = new LocalStorageStore();

export function rememberCurrentSession(sessionId: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(CURRENT_SESSION_KEY, sessionId);
}

export function forgetCurrentSession(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(CURRENT_SESSION_KEY);
}

export function getCurrentSessionId(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(CURRENT_SESSION_KEY);
}

export class MissingSessionError extends Error {
  constructor(sessionId: string) {
    super(`No saved game found for session ${sessionId}. Start a new game.`);
    this.name = "MissingSessionError";
  }
}

export function requirePersisted(sessionId: string): PersistedSession {
  const persisted = sessionStore.load(sessionId);
  if (!persisted) throw new MissingSessionError(sessionId);
  return persisted;
}
