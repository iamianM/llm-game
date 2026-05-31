"use client";

import { useEffect, useRef } from "react";
import { playSfx, preloadSfx } from "../../lib/sfx";
import { useUiStore } from "../../lib/store";

// Bridges store-driven overlay state to the SFX layer so the panels that open
// from anywhere (settings, wardrobe, cast rail) get a consistent open/close
// cue without every trigger site having to remember to play one. Also warms
// the SFX buffers once on mount so the first click isn't a silent miss.
export function SfxBridge() {
  const settingsOpen = useUiStore((s) => s.settingsOpen);
  const wardrobeOpen = useUiStore((s) => s.wardrobeOpen);
  const railOpen = useUiStore((s) => s.rightRailOpen);
  // Seed with the initial (all-closed) state so the first render's effects
  // don't fire a phantom close cue.
  const prev = useRef({ settingsOpen, wardrobeOpen, railOpen });

  useEffect(() => {
    preloadSfx();
  }, []);

  useEffect(() => {
    const was = prev.current;
    if (settingsOpen !== was.settingsOpen) {
      playSfx(settingsOpen ? "modal-open" : "modal-close");
    }
    if (wardrobeOpen !== was.wardrobeOpen) {
      playSfx(wardrobeOpen ? "modal-open" : "modal-close");
    }
    if (railOpen !== was.railOpen) {
      playSfx(railOpen ? "modal-open" : "modal-close");
    }
    prev.current = { settingsOpen, wardrobeOpen, railOpen };
  }, [settingsOpen, wardrobeOpen, railOpen]);

  return null;
}
