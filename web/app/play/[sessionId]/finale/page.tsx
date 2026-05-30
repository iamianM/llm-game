"use client";

import { useQuery } from "@tanstack/react-query";
import { getSession } from "../../../../lib/api";
import { FinaleScreen } from "../../../../components/chrome/FinaleScreen";

export default function FinalePage({ params }: { params: { sessionId: string } }) {
  const query = useQuery({ queryKey: ["session", params.sessionId], queryFn: () => getSession(params.sessionId) });
  if (!query.data) return <main className="grid min-h-screen place-items-center bg-bg text-[var(--card)]">Loading finale...</main>;
  return <FinaleScreen state={query.data.state} sessionId={params.sessionId} />;
}
