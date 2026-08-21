"use client";

import { usePathname } from "next/navigation";
import { AmbiencePlayer } from "./AmbiencePlayer";
import { MusicPlayer } from "./MusicPlayer";
import { SfxBridge } from "./SfxBridge";

export function AppAudio() {
  const pathname = usePathname();

  if (pathname.startsWith("/evals")) return null;

  return (
    <>
      <MusicPlayer />
      <AmbiencePlayer />
      <SfxBridge />
    </>
  );
}
