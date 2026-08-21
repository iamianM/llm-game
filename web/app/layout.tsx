import "./globals.css";
import type { Metadata, Viewport } from "next";
import { QueryProvider } from "../lib/query-provider";
import { AppAudio } from "../components/chrome/AppAudio";

export const metadata: Metadata = {
  title: "Paradise Hearts",
  description: "A reality dating show roguelite."
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>{children}</QueryProvider>
        <AppAudio />
      </body>
    </html>
  );
}
