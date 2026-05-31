"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { getSession } from "../../../../lib/api";
import { FinaleScreen } from "../../../../components/chrome/FinaleScreen";
import { useUiStore } from "../../../../lib/store";

export default function FinalePage({ params }: { params: { sessionId: string } }) {
  const query = useQuery({ queryKey: ["session", params.sessionId], queryFn: () => getSession(params.sessionId) });
  const setMusicScene = useUiStore((s) => s.setMusicScene);
  // The finale is the climactic last night — sit on the evening bed, and hand
  // the score back to the title theme when the player leaves for the menu.
  useEffect(() => {
    setMusicScene("evening");
    return () => setMusicScene("title");
  }, [setMusicScene]);
  if (!query.data) return <main className="grid min-h-screen place-items-center bg-bg text-[var(--card)]">Loading finale...</main>;
  return <FinaleScreen state={query.data.state} sessionId={params.sessionId} />;
}
