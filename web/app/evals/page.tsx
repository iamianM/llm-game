import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "LLM Evals | Paradise Hearts",
  description:
    "A real GPT-5.6 Luna evaluation run across Paradise Hearts narrative scenarios.",
};

export default function EvalsPage() {
  return (
    <main className="fixed inset-0 flex flex-col bg-[#f7f4e7] text-[#282725]">
      <header className="flex h-11 shrink-0 items-center justify-between border-b border-black/15 bg-[#fffdf1] px-4 text-xs">
        <Link
          href="/"
          className="font-semibold uppercase tracking-[0.12em] hover:opacity-60"
        >
          Paradise Hearts
        </Link>
        <span className="text-black/55">Real Luna run · synthetic game data</span>
      </header>
      <iframe
        className="min-h-0 w-full flex-1 border-0"
        src="/evals/report.html"
        title="Paradise Hearts golden LLM evaluation dashboard"
      />
    </main>
  );
}
