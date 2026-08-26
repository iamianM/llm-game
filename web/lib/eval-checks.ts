const EXACT_CHECKS: Record<string, string> = {
  agent_traces_present: "Confirms that a real model call was captured for this turn. It does not grade the writing.",
  background_kind_isolated: "Confirms that off-screen NPC activity did not write private, first-hand memories for the player.",
  ceremony_events_present: "Confirms that the engine recorded at least one structured ceremony event for the narrator to describe.",
  challenge_cleared: "Confirms that a completed challenge no longer blocks the next player action.",
  challenge_resolved: "Confirms that the engine recorded a deterministic challenge result.",
  conversation_active: "Confirms that the conversation remains open with the selected NPC after this action.",
  conversation_closed: "Confirms that the engine closed the active conversation after an exit action.",
  curator_batch_recorded: "Confirms that the memory agent reviewed the closed conversation and returned a typed memory batch, including an empty batch when nothing should be stored.",
  curator_memories: "Confirms that the memory agent returned durable memories for the people involved in the exchange.",
  engine_state_invariants_preserved: "Confirms that the action kept player identity, seeded state, eliminations, couples, and schema boundaries valid.",
  event_narration_present: "Confirms that the narrator returned prose for the resolved event.",
  event_narration_valid: "Confirms that the narration names every participant required by the structured event record.",
  exchange_valid: "Confirms that the dialogue matches the typed exchange schema and does not leak hidden cast or engine state.",
  flush_active: "Confirms that Flush of Hearts is active in engine state after this turn.",
  follow_up_menu_valid: "Confirms that the final player menu keeps every accepted contextual option, uses valid fields, and contains exactly one exit choice.",
  interruption_cleared: "Confirms that the engine consumed the pending interruption after the player's response.",
  mechanical_success: "Confirms that the seeded game calculation resolved this authored beat as a success.",
  no_agent_validation_retries: "Confirms that every model response passed its typed contract on the first attempt.",
  no_exchange: "Confirms that this engine-only action did not make an unnecessary dialogue-model call.",
  npc_conversation_closed: "Confirms that a successful private chat closed the NPC-to-NPC conversation with an explicit engine record.",
  npc_conversation_still_active: "Confirms that a rejected private-chat attempt did not erase the NPC-to-NPC conversation.",
  pending_gather_waiting: "Confirms that the engine is waiting for the player to enter the scheduled group event.",
  pending_npc_proposal_cleared: "Confirms that responding to an NPC proposal consumed the pending proposal.",
  private_chat_recorded: "Confirms that the engine recorded the private-chat chance, roll, target, and outcome.",
  private_chat_rejected: "Confirms that the deterministic private-chat roll resolved as a rejection.",
  private_chat_rejection_witness_memory: "Confirms that the rejection left an appropriate witnessed memory in the social graph.",
  private_chat_succeeded: "Confirms that the deterministic private-chat roll resolved as a success.",
  resort_update_committed: "Confirms that the background resort agent returned a typed update that the engine accepted.",
  run_outcome_present: "Confirms that the engine recorded the final result of the season.",
};

const PREFIX_CHECKS: Array<[string, string]> = [
  ["active_conversation_target_is:", "Confirms that the engine kept the conversation open with the named NPC."],
  ["audience_delta:", "Confirms that the engine applied the exact expected audience-score change."],
  ["ceremony_event_present:", "Confirms that the engine recorded the named ceremony event before narration."],
  ["couple_present:", "Confirms that the named pair exists in the engine's couple state."],
  ["curator_memories_for:", "Confirms that the memory agent wrote a durable memory for the named participant."],
  ["forced_movement_present:", "Confirms that the engine recorded the expected forced NPC movement."],
  ["location_is:", "Confirms that the player ended the turn at the expected location."],
  ["pending_npc_proposal_from:", "Confirms that the engine has a pending proposal from the named NPC."],
  ["private_suite_consumed:", "Confirms that the Private Suite state and relationship changes were applied once for the named partner."],
  ["proposal_outcome_is:", "Confirms that the engine stored the expected accepted or rejected proposal outcome."],
  ["relationship_delta:", "Confirms that the engine applied the exact expected relationship-stat change to the named NPC."],
  ["visible_targets_include:", "Confirms that the named, non-eliminated NPCs are visible at the player's location."],
];

export function evalCheckExplanation(id: string): string {
  const exact = EXACT_CHECKS[id];
  if (exact) return exact;
  const prefixed = PREFIX_CHECKS.find(([prefix]) => id.startsWith(prefix));
  return prefixed?.[1] ?? "Confirms a structured engine or schema contract for this turn. It does not judge prose quality.";
}

export function isDocumentedEvalCheck(id: string): boolean {
  return Boolean(EXACT_CHECKS[id] || PREFIX_CHECKS.some(([prefix]) => id.startsWith(prefix)));
}
