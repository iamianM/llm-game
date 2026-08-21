import type { AvailableAction, SessionState, TurnResponse } from "../types";
import type { CharacterPose, Position, SceneBeat } from "./types";

export type PresentationTransition =
  | {
      kind: "baseline";
      state: SessionState;
      actions: readonly AvailableAction[];
    }
  | {
      kind: "pending";
      previous: SessionState;
      state: SessionState;
      actions: readonly AvailableAction[];
      selectedAction: AvailableAction;
      stream: {
        speakerId: string | null;
        speakerName: string | null;
        text: string;
      };
    }
  | {
      kind: "resolved";
      previous: SessionState;
      response: TurnResponse;
    };

export type ActionLanes = {
  character: readonly AvailableAction[];
  move: readonly AvailableAction[];
  fan: readonly AvailableAction[];
};

export type SceneCastMember = {
  id: string;
  position: Position;
  pose: CharacterPose;
  focused: boolean;
};

export type SceneFrame = {
  cast: readonly SceneCastMember[];
  groupPanelIds: readonly string[];
};

export type SceneFeature =
  | {
      id: string;
      kind: "ceremony";
      event: TurnResponse["ceremony_events"][number];
    }
  | {
      id: string;
      kind: "recap";
      recap: SessionState["daily_recaps"][number];
    };

export type SceneSegment<TSlot = never> = {
  id: string;
  beats: readonly SceneBeat[];
  slot: TSlot | null;
};

export type ScenePlan<TSlot = never> = {
  id: string;
  locationId: string;
  segments: readonly SceneSegment<TSlot>[];
  frames: readonly SceneFrame[];
  actionLanes: ActionLanes;
  features: readonly SceneFeature[];
};

export interface MinigamePresentationPort<TSlot> {
  plan(transition: PresentationTransition): SceneSegment<TSlot> | null;
}
