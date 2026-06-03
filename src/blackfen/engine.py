"""Deterministic turn engine for Blackfen Road."""

from __future__ import annotations

from src.blackfen.agents.intent import IntentParser, LocalIntentParser
from src.blackfen.agents.narrator import MockNarrator, Narrator
from src.blackfen.content import load_world
from src.blackfen.dice import roll_d20, roll_damage
from src.blackfen.hash import state_hash
from src.blackfen.models import (
    Ability,
    GameState,
    Intent,
    IntentKind,
    MechanicalResult,
    MonsterState,
    RollRecord,
    RunStatus,
    TurnRecord,
)
from src.blackfen.rng import SeededRng


def run_turn(
    state: GameState,
    raw_text: str,
    rng: SeededRng,
    *,
    parser: IntentParser | None = None,
    narrator: Narrator | None = None,
) -> TurnRecord:
    """Parse, resolve, narrate, and record one Blackfen Road turn."""
    if state.status is not RunStatus.ACTIVE:
        raise ValueError("this run has ended")
    input_hash = state_hash(state)
    intent = (parser or LocalIntentParser()).parse(state, raw_text)
    result = resolve_intent(state, intent, rng)
    state.turn_index += 1
    narration = (narrator or MockNarrator()).narrate(state, result)
    output_hash = state_hash(state)
    record = TurnRecord(
        turn_index=state.turn_index,
        input_hash=input_hash,
        raw_text=raw_text,
        intent=intent,
        mechanical_result=result,
        narration=narration,
        output_hash=output_hash,
    )
    state.turns.append(record)
    return record


def resolve_intent(state: GameState, intent: Intent, rng: SeededRng) -> MechanicalResult:
    """Apply a typed intent to state."""
    if intent.kind is IntentKind.TRAVEL:
        return _travel(state, intent)
    if intent.kind is IntentKind.TALK:
        return _talk(state, intent)
    if intent.kind is IntentKind.ATTACK:
        return _attack(state, intent, rng)
    if intent.kind is IntentKind.REST:
        return _rest(state, intent, rng)
    if intent.kind is IntentKind.USE_ITEM:
        return _use_item(state, intent)
    if intent.kind is IntentKind.COMMAND_COMPANION:
        return _command_companion(state, intent)
    return _inspect(state, intent, rng)


def _travel(state: GameState, intent: Intent) -> MechanicalResult:
    world = load_world()
    if intent.target_id is None:
        raise ValueError("travel needs a destination")
    if intent.target_id not in world.locations:
        raise ValueError(f"unknown destination: {intent.target_id}")
    target = world.locations[intent.target_id]
    current = world.locations[state.current_location_id]
    if target.required_flag and target.required_flag not in state.quest_flags:
        raise ValueError(f"{target.name} is not reachable yet")
    if intent.target_id not in state.known_locations and intent.target_id not in current.exits:
        raise ValueError(f"{target.name} is not known from here")
    if intent.target_id not in current.exits and intent.target_id != state.current_location_id:
        raise ValueError(f"{target.name} is not connected to {current.name}")
    state.current_location_id = intent.target_id
    if intent.target_id not in state.visited_locations:
        state.visited_locations.append(intent.target_id)
    _ensure_encounter_state(state)
    return MechanicalResult(intent=intent, summary=f"You travel to {target.name}.")


def _talk(state: GameState, intent: Intent) -> MechanicalResult:
    world = load_world()
    location = world.locations[state.current_location_id]
    target_id = intent.target_id or (location.npcs[0] if location.npcs else None)
    if target_id is None or target_id not in location.npcs:
        raise ValueError("there is no one here to talk to")
    npc = world.npcs[target_id]
    flags = [flag for flag in npc.knows if flag not in state.quest_flags]
    state.quest_flags.extend(flags)
    discovered = _reveal_from_flags(state)
    note = f"{npc.name} says: {npc.dialogue_seed}"
    state.journal.append(note)
    return MechanicalResult(intent=intent, summary=f"You speak with {npc.name}.", details=[note], discovered_flags=flags, discovered_locations=discovered)


def _inspect(state: GameState, intent: Intent, rng: SeededRng) -> MechanicalResult:
    world = load_world()
    location = world.locations[state.current_location_id]
    if state.current_location_id == "barrow_crypt" and "drowned_knight_defeated" in state.quest_flags:
        state.status = RunStatus.VICTORY
        return MechanicalResult(
            intent=intent,
            summary="You lay the shrine bell clapper against the drowned knight's oath-stone.",
            details=["The iron answers with one clean note. The water pulls back from the crypt steps."],
            run_status=state.status,
        )
    roll = roll_d20(rng, "wisdom check", state.player.abilities.get(Ability.WISDOM, 0), target=11)
    flags: list[str] = []
    details: list[str] = []
    if intent.approach == "fallback_inspect":
        details.append("I treated that as looking around for anything useful.")
    if roll.total >= 11:
        flags.extend(flag for flag in location.secrets if flag not in state.quest_flags)
        state.quest_flags.extend(flags)
        details.append("You find the detail everyone else missed.")
    else:
        details.append("You search carefully, but the useful pattern stays just out of reach.")
    discovered = _reveal_location_ids(state, location.reveal_locations)
    items_gained: list[str] = []
    if state.current_location_id == "hill_shrine" and "shrine_bell_token" not in state.player.inventory:
        state.player.inventory.append("shrine_bell_token")
        items_gained.append("shrine_bell_token")
        if "has_shrine_bell" not in state.quest_flags:
            state.quest_flags.append("has_shrine_bell")
            flags.append("has_shrine_bell")
    if state.current_location_id == "sunken_chapel" and "has_shrine_bell" in state.quest_flags and "barrow_opened" not in state.quest_flags:
        state.quest_flags.append("barrow_opened")
        flags.append("barrow_opened")
    if state.current_location_id == "barrow_crypt" and "drowned_knight_defeated" in state.quest_flags:
        state.status = RunStatus.VICTORY
    return MechanicalResult(intent=intent, rolls=[roll], summary=f"You inspect {location.name}.", details=details, discovered_flags=flags, discovered_locations=discovered, items_gained=items_gained, run_status=state.status)


def _attack(state: GameState, intent: Intent, rng: SeededRng) -> MechanicalResult:
    world = load_world()
    monsters = _ensure_encounter_state(state)
    if not monsters:
        return MechanicalResult(intent=intent, summary="There is nothing here that needs a blade.")
    target = monsters[0]
    monster_def = world.monsters[target.id]
    rolls: list[RollRecord] = []
    details: list[str] = []
    damage_to_enemies = 0
    player_roll = roll_d20(rng, "player attack", state.player.attack_bonus, monster_def.armor_class)
    rolls.append(player_roll)
    if player_roll.total >= monster_def.armor_class:
        damage = roll_damage(rng, state.player.damage)
        target.hp -= damage
        damage_to_enemies += damage
        details.append(f"You hit the {monster_def.name} for {damage}.")
    else:
        details.append(f"You miss the {monster_def.name}.")
    if target.hp <= 0:
        details.append(f"The {monster_def.name} drops.")
        monsters.pop(0)
    _companion_turn(state, monsters, rng, rolls, details)
    damage_to_player, damage_to_companion = _enemy_turn(state, monsters, rng, rolls, details)
    items_gained: list[str] = []
    flags: list[str] = []
    if not monsters:
        items_gained, flags = _resolve_encounter(state)
        details.append("The fight is over.")
    if state.player.hp <= 0:
        state.status = RunStatus.DEAD
    return MechanicalResult(intent=intent, rolls=rolls, summary="Steel, nerve, and bad luck decide the moment.", details=details, damage_to_player=damage_to_player, damage_to_companion=damage_to_companion, damage_to_enemies=damage_to_enemies, items_gained=items_gained, discovered_flags=flags, run_status=state.status)


def _rest(state: GameState, intent: Intent, rng: SeededRng) -> MechanicalResult:
    world = load_world()
    location = world.locations[state.current_location_id]
    roll = roll_d20(rng, "rest safety", state.player.abilities.get(Ability.WISDOM, 0), target=8)
    if location.kind == "settlement" or roll.total >= 8:
        before = state.player.hp
        state.player.hp = min(state.player.max_hp, state.player.hp + 6)
        state.companion.hp = min(state.companion.max_hp, state.companion.hp + 4)
        return MechanicalResult(intent=intent, rolls=[roll], summary=f"You catch your breath and recover {state.player.hp - before} HP.")
    state.player.hp = max(0, state.player.hp - 2)
    if state.player.hp <= 0:
        state.status = RunStatus.DEAD
    return MechanicalResult(intent=intent, rolls=[roll], summary="Your rest is broken by cold rain and something moving nearby.", damage_to_player=2, run_status=state.status)


def _use_item(state: GameState, intent: Intent) -> MechanicalResult:
    item_id = intent.target_id or "healing_potion"
    world = load_world()
    if item_id not in state.player.inventory:
        raise ValueError(f"you do not have {item_id}")
    item = world.items[item_id]
    if item.kind != "consumable":
        raise ValueError(f"{item.name} cannot be used this way")
    state.player.inventory.remove(item_id)
    before = state.player.hp
    state.player.hp = min(state.player.max_hp, state.player.hp + item.heal)
    return MechanicalResult(intent=intent, summary=f"You use {item.name} and recover {state.player.hp - before} HP.", items_lost=[item_id])


def _command_companion(state: GameState, intent: Intent) -> MechanicalResult:
    text = (intent.approach or "").lower()
    if "attack" in text or "aggressive" in text:
        state.companion.stance = "aggressive"
    elif "careful" in text or "cautious" in text or "back" in text:
        state.companion.stance = "cautious"
    else:
        state.companion.stance = "support"
    return MechanicalResult(intent=intent, summary=f"Elian shifts to a {state.companion.stance} stance.")


def _ensure_encounter_state(state: GameState) -> list[MonsterState]:
    world = load_world()
    location = world.locations[state.current_location_id]
    if location.encounter is None or location.encounter in state.resolved_encounters:
        return []
    if location.encounter not in state.active_monsters:
        encounter = world.encounters[location.encounter]
        state.active_monsters[location.encounter] = [MonsterState(id=monster_id, instance_id=f"{location.encounter}-{index}", hp=world.monsters[monster_id].hit_points) for index, monster_id in enumerate(encounter.monsters)]
    return state.active_monsters[location.encounter]


def _companion_turn(state: GameState, monsters: list[MonsterState], rng: SeededRng, rolls: list[RollRecord], details: list[str]) -> None:
    if not monsters or state.companion.hp <= 0:
        return
    world = load_world()
    target = monsters[0]
    monster_def = world.monsters[target.id]
    roll = roll_d20(rng, "Elian attack", state.companion.attack_bonus, monster_def.armor_class)
    rolls.append(roll)
    if roll.total >= monster_def.armor_class:
        damage = roll_damage(rng, state.companion.damage)
        target.hp -= damage
        details.append(f"Elian hits the {monster_def.name} for {damage}.")
        if target.hp <= 0:
            details.append(f"Elian finishes the {monster_def.name}.")
            monsters.pop(0)
    else:
        details.append(f"Elian misses the {monster_def.name}.")


def _enemy_turn(state: GameState, monsters: list[MonsterState], rng: SeededRng, rolls: list[RollRecord], details: list[str]) -> tuple[int, int]:
    world = load_world()
    damage_to_player = 0
    damage_to_companion = 0
    for monster in monsters:
        monster_def = world.monsters[monster.id]
        target_companion = state.companion.stance == "aggressive" and state.companion.hp > 0
        armor = state.companion.armor_class if target_companion else state.player.armor_class
        roll = roll_d20(rng, f"{monster_def.name} attack", monster_def.attack_bonus, armor)
        rolls.append(roll)
        if roll.total < armor:
            details.append(f"The {monster_def.name} misses.")
            continue
        damage = roll_damage(rng, monster_def.damage)
        if target_companion:
            state.companion.hp = max(0, state.companion.hp - damage)
            damage_to_companion += damage
            details.append(f"The {monster_def.name} wounds Elian for {damage}.")
        else:
            state.player.hp = max(0, state.player.hp - damage)
            damage_to_player += damage
            details.append(f"The {monster_def.name} wounds you for {damage}.")
    return damage_to_player, damage_to_companion


def _resolve_encounter(state: GameState) -> tuple[list[str], list[str]]:
    world = load_world()
    location = world.locations[state.current_location_id]
    if location.encounter is None:
        return [], []
    encounter = world.encounters[location.encounter]
    if location.encounter not in state.resolved_encounters:
        state.resolved_encounters.append(location.encounter)
    gained = [item for item in encounter.treasure if item not in state.player.inventory]
    state.player.inventory.extend(gained)
    flags = [flag for flag in encounter.reveal_flags if flag not in state.quest_flags]
    state.quest_flags.extend(flags)
    if location.encounter == "barrow_knight" and "drowned_knight_defeated" not in state.quest_flags:
        state.quest_flags.append("drowned_knight_defeated")
    _reveal_from_flags(state)
    return gained, flags


def _reveal_from_flags(state: GameState) -> list[str]:
    reveal_ids: list[str] = []
    if "caravan_taken_north" in state.quest_flags:
        reveal_ids.extend(["rusted_watchtower", "witchwood"])
    if "bell_fears_dead" in state.quest_flags or "has_shrine_bell" in state.quest_flags:
        reveal_ids.append("sunken_chapel")
    if "smuggler_key_clue" in state.quest_flags:
        reveal_ids.append("smuggler_tunnel")
    if "barrow_opened" in state.quest_flags:
        reveal_ids.append("barrow_crypt")
    return _reveal_location_ids(state, reveal_ids)


def _reveal_location_ids(state: GameState, location_ids: list[str]) -> list[str]:
    discovered: list[str] = []
    for location_id in location_ids:
        if location_id not in state.known_locations:
            state.known_locations.append(location_id)
            discovered.append(location_id)
    return discovered

