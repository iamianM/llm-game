"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { DEFAULT_USE_LIVE_LLM, useUiStore } from "./store";

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [client] = useState(() => new QueryClient());
  const setUseLive = useUiStore((s) => s.setUseLiveLlm);
  // Hydrate the live-LLM toggle from localStorage on first client render.
  // Reading at store-create time misses the SSR pass (window undefined), so
  // the initial render falls back to false; this effect reads the real value
  // before the casting page commits and the toggle gets locked into Demo.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const stored = window.localStorage.getItem("paradise.settings.useLiveLlm");
    if (stored === "1") setUseLive(true);
    if (stored === "0") setUseLive(false);
    if (stored === null && DEFAULT_USE_LIVE_LLM) setUseLive(true);
  }, [setUseLive]);
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
