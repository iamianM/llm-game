"""Mock-mode Question Bank generator.

See ``docs/minigame-system.md`` §4. The bank is generated once per season
from existing Trait Cards. In mock mode (no live LLM) this module produces
deterministic stems by trait_key. A live OpenAI Question Bank agent ships
as a follow-up PR; until then mock-mode output is sufficient because the
canonical truth (``correct_value`` and ``distractors``) is pulled from the
Trait Card and never invented by either path.
"""

from __future__ import annotations

from src.game.state.event_models import QuestionBank, QuestionBankPrompt
from src.game.state.models import GameState

# Stems keyed by trait_key. Live agent rephrases these; mock keeps them stable.
_STEMS: dict[str, str] = {
    "occupation": "What does {name} do for work back home?",
    "hometown": "Where is {name} from?",
    "age": "How old is {name}?",
    "favorite_food": "What's {name}'s favourite meal?",
    "hobby": "How does {name} actually like to spend a Sunday?",
    "drink_of_choice": "What's {name}'s drink of choice?",
    "biggest_fear": "What's {name}'s biggest fear?",
    "love_language": "What's {name}'s love language?",
    "worst_habit": "What's {name}'s worst habit?",
    "pet_peeve": "What's {name}'s biggest pet peeve?",
    "insecurity": "What is {name} most insecure about?",
    "past_heartbreak": "What was {name}'s last heartbreak?",
    "hidden_secret": "What's the one thing {name} is hiding from the villa?",
}


def build_question_bank(state: GameState) -> QuestionBank:
    """Build the season's Question Bank from Trait Cards.

    Deterministic: same seed + same cast = same bank. Sub-seed derived from
    ``state.seed`` per ``docs/minigame-system.md`` §4.
    """
    bank_seed = state.seed * 2654435761 & 0xFFFFFFFF  # Knuth multiplicative hash
    prompts: dict[str, list[QuestionBankPrompt]] = {"compatibility_quiz": []}
    for islander in sorted(state.islanders, key=lambda i: i.id):
        card = islander.trait_card
        for key in sorted(card.core_traits):
            fact = card.core_traits[key]
            prompts["compatibility_quiz"].append(
                QuestionBankPrompt(
                    id=f"cq_{islander.id}_{key}",
                    minigame_kind="compatibility_quiz",
                    target_id=islander.id,
                    trait_key=key,
                    tier=fact.tier,
                    mechanical=fact.mechanical,
                    stem=_stem_for(islander.name, key),
                    correct_value=fact.value,
                    distractors=list(fact.distractors),
                )
            )
        for key in sorted(card.flavor_traits):
            fact = card.flavor_traits[key]
            prompts["compatibility_quiz"].append(
                QuestionBankPrompt(
                    id=f"cq_{islander.id}_{key}",
                    minigame_kind="compatibility_quiz",
                    target_id=islander.id,
                    trait_key=key,
                    tier=fact.tier,
                    mechanical=fact.mechanical,
                    stem=_stem_for(islander.name, key),
                    correct_value=fact.value,
                    distractors=list(fact.distractors),
                )
            )
    return QuestionBank(bank_seed=bank_seed, prompts=prompts)


def _stem_for(name: str, key: str) -> str:
    template = _STEMS.get(key, f"Tell us about {{name}}'s {key.replace('_', ' ')}.")
    return template.format(name=name)


def ensure_question_bank(state: GameState) -> None:
    """Populate ``state.question_bank`` if it is not already built."""
    if state.question_bank is None:
        state.question_bank = build_question_bank(state)
