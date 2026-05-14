export function Narration({ children }: { children: string }) {
  return <p className="mx-auto mt-6 max-w-2xl font-display text-2xl leading-10 text-[var(--card)]">{children}</p>;
}
