"use client";

import type { SessionState } from "../../lib/types";
import type { HeartbreakerLook } from "../../lib/look";
import { PLAYER_ANCHOR, PLAYER_ANCHOR_COMPACT, npcPositions } from "../../lib/scene/positions";
import type { CharacterPose, Position } from "../../lib/scene/types";
import { CharacterSprite } from "./CharacterSprite";

type Props = {
  state: SessionState;
  look?: HeartbreakerLook | null;
  focusedId: string | null;
  speakerPose: CharacterPose;
  // The bottom choice fan is open — the player tucks up + shrinks (mobile) so
  // the option bars never sit on top of the standee.
  choicesActive?: boolean;
  tappableIds?: Set<string>;
  onCharacterTap?: (id: string) => void;
};

export function CharacterLayer({ state, look = null, focusedId, speakerPose, choicesActive = false, tappableIds, onCharacterTap }: Props) {
  const npcs = visibleNpcs(state, focusedId);
  const focusedIndex = focusedId ? npcs.findIndex((npc) => npc.id === focusedId) : null;
  const positions = npcPositions(npcs.length, focusedIndex !== null && focusedIndex >= 0 ? focusedIndex : null);
  return (
    <div className="character-layer" aria-label="Sunset Bay scene characters">
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
          tappable={tappableIds?.has(npc.id) ?? false}
          onTap={onCharacterTap ? () => onCharacterTap(npc.id) : undefined}
        />
      ))}
      <CharacterSprite
        id={state.player.id}
        name={look?.name?.trim() || state.player.name || "You"}
        role="player"
        gender={look?.gender ?? state.player.gender}
        archetypeId={look?.archetype ?? state.player.archetype_id}
        look={look}
        position={choicesActive ? PLAYER_ANCHOR_COMPACT : PLAYER_ANCHOR}
        pose={focusedId === state.player.id ? "talking" : "listening"}
        active={focusedId === state.player.id}
        compact={choicesActive}
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

// Only show heartbreakers in the player's current location. The focused NPC (if
// any) is always included so quiz scenes work even when the target's room
// differs (e.g. a Producer-text gather). During Day-1 intros the entire
// cast appears at the flame_deck visually regardless of their canonical room.
export function visibleNpcs(state: Props["state"], focusedId: string | null) {
  const allHere = state.phase === "intros";
  return state.heartbreakers.filter((heartbreaker) => {
    if (heartbreaker.eliminated) return false;
    if (allHere) return true;
    if (focusedId && heartbreaker.id === focusedId) return true;
    return heartbreaker.location_id === state.location_id;
  });
}
