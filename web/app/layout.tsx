import "./globals.css";
import type { Metadata } from "next";
import { QueryProvider } from "../lib/query-provider";
import { MusicPlayer } from "../components/chrome/MusicPlayer";

export const metadata: Metadata = {
  title: "Paradise Hearts",
  description: "A reality dating show roguelite."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>{children}</QueryProvider>
        <MusicPlayer />
      </body>
    </html>
  );
}
