import type {
  MinigamePresentationPort,
  PresentationTransition,
  SceneSegment,
} from "../scene/presentation";
import type { SceneBeat } from "../scene/types";
import { presentMinigame, type MinigamePresentation } from "./presentation";

/** Compose typed minigame presentation into the generic scene playback seam. */
export const MINIGAME_SCENE_PRESENTATION: MinigamePresentationPort<MinigamePresentation> = {
  plan(transition: PresentationTransition): SceneSegment<MinigamePresentation> | null {
    const state = transition.kind === "resolved" ? transition.response.state : transition.state;
    const actions = transition.kind === "resolved"
      ? transition.response.available_actions
      : transition.actions;
    const view = state.pending_challenge;
    if (view === null) return null;

    const presentation = presentMinigame(view, actions);
    const beats: SceneBeat[] = [
      { kind: "camera", shot: "minigame_board", focusIds: [], durationMs: 120 },
    ];
    if (presentation.narration.trim()) {
      beats.push({
        kind: "narrator",
        text: presentation.narration,
        sourceEventId: presentation.id,
      });
    }
    if (presentation.status === "round") {
      beats.push({ kind: "choice_fan", spec: { actions: [...presentation.choices] } });
    }
    return {
      id: `minigame:${presentation.id}`,
      beats,
      slot: presentation,
    };
  },
};
