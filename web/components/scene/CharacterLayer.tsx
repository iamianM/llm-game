"use client";

import type { SessionState } from "../../lib/types";
import { PLAYER_ANCHOR, npcPositions } from "../../lib/scene/positions";
import type { CharacterPose, Position } from "../../lib/scene/types";
import { CharacterSprite } from "./CharacterSprite";

type Props = {
  state: SessionState;
  focusedId: string | null;
  speakerPose: CharacterPose;
};

export function CharacterLayer({ state, focusedId, speakerPose }: Props) {
  const npcs = state.islanders.filter((islander) => !islander.eliminated);
  const focusedIndex = focusedId ? npcs.findIndex((npc) => npc.id === focusedId) : null;
  const positions = npcPositions(npcs.length, focusedIndex !== null && focusedIndex >= 0 ? focusedIndex : null);
  return (
    <div className="character-layer" aria-label="Villa scene characters">
      {npcs.map((npc, index) => (
        <CharacterSprite
          key={npc.id}
          id={npc.id}
          name={npc.name}
          role="npc"
          gender={npc.gender}
          position={positions[index] ?? fallbackNpcPosition(index)}
          pose={focusedId === npc.id ? speakerPose : "listening"}
          active={focusedId === npc.id}
        />
      ))}
      <CharacterSprite
        id={state.player.id}
        name={state.player.name || "You"}
        role="player"
        gender={state.player.gender}
        archetypeId={state.player.archetype_id}
        position={PLAYER_ANCHOR}
        pose={focusedId === state.player.id ? "talking" : "listening"}
        active={focusedId === state.player.id}
      />
      <style jsx>{`
        .character-layer {
          position: absolute;
          inset: 0;
          z-index: 3;
          pointer-events: none;
        }
      `}</style>
    </div>
  );
}

function fallbackNpcPosition(index: number): Position {
  return { x: 22 + index * 7, y: 58, scale: 0.62, dimmed: true };
}
