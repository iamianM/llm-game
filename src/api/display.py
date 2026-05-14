"""Player-facing Paradise Hearts display translations."""

from __future__ import annotations

DISPLAY_NAMES: dict[str, str] = {
    "audience_appeal": "Heart Beats",
    "bombshell": "Heart Throb",
    "casa_amor": "Flush of Hearts",
    "casa_amor_announce": "Flush of Hearts Announcement",
    "casa_amor_arrival": "Flush of Hearts Arrival",
    "casa_amor_decision": "Flush of Hearts Decision",
    "casa_amor_return_reveal": "Sunset Bay Return",
    "casa_return": "Sunset Bay Return",
    "casa_pool": "Flush of Hearts Pool",
    "casa_kitchen": "Flush of Hearts Kitchen",
    "casa_terrace": "Flush of Hearts Terrace",
    "challenge": "Challenge",
    "compatibility_quiz": "Compatibility Quiz",
    "complete": "Complete",
    "evening": "Evening",
    "elimination": "Heart Out",
    "firepit": "Firepit",
    "final_couples": "Final Couples Challenge",
    "graft": "Spark",
    "heart_rate": "Pulse Race",
    "hideaway": "Paradise Suite",
    "intros": "Day-1 Introductions",
    "kitchen": "Kitchen",
    "lie_detector": "Lie Detector",
    "morning": "Morning",
    "main": "Sunset Bay",
    "mr_and_mrs": "The Couples Quiz",
    "opening": "First Spark",
    "pool": "Pool",
    "proposal": "Heart Swap Proposal",
    "producer_text": "Paradise Calls",
    "public_perception": "Pulse",
    "recouple": "Heart Swap",
    "recouple_proposal": "Heart Swap Proposal",
    "recoupling": "Pairing Ceremony",
    "snog_marry_pie": "Kiss Wed Pass",
    "text": "Paradise Calls",
    "terrace": "Terrace",
}


def display(value: str) -> str:
    """Return Paradise Hearts copy for an engine identifier."""
    return DISPLAY_NAMES.get(value, value.replace("_", " ").title())


def translate_text(value: str) -> str:
    """Translate legacy/internal show terms inside engine-authored prose."""
    return (
        value.replace("The villa gathers", "Everyone gathers")
        .replace("The Villa gathers", "Everyone gathers")
        .replace("I've got a text", "Paradise Calls")
        .replace("I'VE GOT A TEXT", "PARADISE CALLS")
        .replace("Heart Appeal", "Heart Beats")
        .replace("Audience Appeal", "Heart Beats")
        .replace("audience appeal", "Heart Beats")
        .replace("public perception", "Pulse")
        .replace("Public Perception", "Pulse")
        .replace("Casa Amor return reveal", "Sunset Bay return")
        .replace("Casa Amor Return", "Sunset Bay Return")
        .replace("Casa Amor return", "Sunset Bay return")
        .replace("Casa Amor", "Flush of Hearts")
        .replace("Flush of Hearts return reveal", "Sunset Bay return")
        .replace("Wild Hearts", "Flush of Hearts")
        .replace("casa amor", "Flush of Hearts")
        .replace("return_with_original", "return with your original couple")
        .replace("return_with_new", "return with a new connection")
        .replace("return_single", "return single")
        .replace("second Sunset Bay", "Flush of Hearts")
        .replace("second villa", "Flush of Hearts")
        .replace("Bombshell", "Heart Throb")
        .replace("bombshell", "Heart Throb")
        .replace("Dumping", "Heart Out")
        .replace("dumping", "Heart Out")
        .replace("dumped", "Heart Out")
        .replace("Steal attempt", "Heart Swap attempt")
        .replace("steal attempt", "Heart Swap attempt")
        .replace("Partner stolen", "Partner Heart Swapped")
        .replace("Recoupling ceremony", "Pairing Ceremony")
        .replace("recoupling ceremony", "pairing ceremony")
        .replace("Recoupling proposal", "Heart Swap Proposal")
        .replace("recoupling proposal", "Heart Swap proposal")
        .replace("Recoupling", "Pairing Ceremony")
        .replace("recoupling", "pairing ceremony")
        .replace("recouples", "swaps hearts")
        .replace("Recouples", "Swaps hearts")
        .replace("recouple", "Heart Swap")
        .replace("Recouple", "Heart Swap")
        .replace("First Pairing", "First Spark")
        .replace("first pairing", "First Spark")
        .replace("Hideaway", "Paradise Suite")
        .replace("hideaway", "Paradise Suite")
        .replace("Grafting", "Sparking")
        .replace("grafting", "Sparking")
        .replace("Graft", "Spark")
        .replace("graft", "Spark")
        .replace("Islanders", "Heartbreakers")
        .replace("islanders", "Heartbreakers")
        .replace("Islander", "Heartbreaker")
        .replace("islander", "heartbreaker")
        .replace("Villa", "Sunset Bay")
        .replace("villa", "Sunset Bay")
    )
