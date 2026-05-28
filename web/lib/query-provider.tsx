"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useUiStore } from "./store";

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [client] = useState(() => new QueryClient());
  const setUseLive = useUiStore((s) => s.setUseLiveLlm);
  // Hydrate the live-LLM toggle from localStorage on first client render.
  // Reading at store-create time misses the SSR pass (window undefined), so
  // the initial render falls back to false; this effect pulls the real value
  // before the new-run page commits and the toggle gets locked into Demo.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const stored = window.localStorage.getItem("paradise.settings.useLiveLlm");
    if (stored === "1") setUseLive(true);
  }, [setUseLive]);
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
