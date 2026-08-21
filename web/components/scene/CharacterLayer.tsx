"use client";

import type { HeartbreakerLook } from "../../lib/look";
import type { SceneFrame } from "../../lib/scene/presentation";
import type { SessionState } from "../../lib/types";
import { CharacterSprite } from "./CharacterSprite";

type Props = {
  state: SessionState;
  frame: SceneFrame;
  look?: HeartbreakerLook | null;
  tappableIds?: ReadonlySet<string>;
  onCharacterTap?: (id: string) => void;
};

export function CharacterLayer({
  state,
  frame,
  look = null,
  tappableIds,
  onCharacterTap,
}: Props) {
  const groupNames = frame.groupPanelIds.map((id) => heartbreakerById(state, id).name);
  return (
    <div className="character-layer" aria-label="Sunset Bay scene characters">
      {frame.cast.map((member) => {
        if (member.id === state.player.id) {
          return (
            <CharacterSprite
              key={member.id}
              id={state.player.id}
              name={look?.name?.trim() || state.player.name || "You"}
              role="player"
              gender={look?.gender ?? state.player.gender}
              archetypeId={look?.archetype ?? state.player.archetype_id}
              look={look}
              position={member.position}
              pose={member.pose}
              active={member.focused}
              compact={member.position.scale < 1.1}
            />
          );
        }
        const npc = heartbreakerById(state, member.id);
        return (
          <CharacterSprite
            key={npc.id}
            id={npc.id}
            name={npc.name}
            role="npc"
            gender={npc.gender}
            position={member.position}
            pose={member.pose}
            active={member.focused}
            tappable={tappableIds?.has(npc.id) ?? false}
            onTap={onCharacterTap ? () => onCharacterTap(npc.id) : undefined}
          />
        );
      })}
      {groupNames.length > 0 ? (
        <aside className="group-panel" data-testid="scene-group-panel" aria-label="Other Heartbreakers here">
          <span>Also here</span>
          <strong>{groupNames.join(" · ")}</strong>
        </aside>
      ) : null}
      <style jsx>{`
        .character-layer {
          position: absolute;
          inset: 0;
          z-index: 3;
          pointer-events: none;
        }
        .group-panel {
          position: absolute;
          top: 12px;
          right: 12px;
          z-index: 5;
          display: grid;
          max-width: min(280px, 58vw);
          gap: 2px;
          padding: 7px 10px;
          border: 1px solid rgba(217,167,58,.3);
          border-radius: var(--r-md);
          background: rgba(8,6,4,.66);
          color: var(--ink-on-dark);
          text-align: right;
        }
        .group-panel span {
          color: var(--gold-soft);
          font-size: 9px;
          letter-spacing: .12em;
          text-transform: uppercase;
        }
        .group-panel strong {
          font-family: var(--font-display);
          font-size: 12px;
          font-weight: 500;
        }
      `}</style>
    </div>
  );
}

function heartbreakerById(state: SessionState, id: string) {
  const heartbreaker = state.heartbreakers.find((candidate) => candidate.id === id);
  if (!heartbreaker) throw new Error(`Scene frame references unknown Heartbreaker: ${id}.`);
  return heartbreaker;
}
