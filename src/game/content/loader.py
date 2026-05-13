"""Markdown content loader and index builder.

This should follow the useful pattern from `steno-livekit-agent` authoring:
load structured markdown, validate with Pydantic, and expose indexed content
snippets to the engine and Narrator.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar, cast

import yaml

from src.game.content.models import (
    ArchetypeContent,
    CasaAmorCastContent,
    ChallengeContent,
    ContentIndex,
    LocationContent,
    PlayerArchetypeContent,
    ProducerTextContent,
)

ContentT = TypeVar(
    "ContentT",
    ArchetypeContent,
    LocationContent,
    PlayerArchetypeContent,
    ChallengeContent,
    ProducerTextContent,
    CasaAmorCastContent,
)


def load_content(root: Path = Path("content")) -> ContentIndex:
    """Load all runtime markdown content."""
    return ContentIndex(
        archetypes=_load_collection(root / "archetypes", ArchetypeContent),
        locations=_load_collection(root / "locations", LocationContent),
        player_archetypes=_load_collection(root / "player_archetypes", PlayerArchetypeContent),
        challenges=_load_collection(root / "challenges", ChallengeContent),
        producer_texts=_load_collection(root / "producer_texts", ProducerTextContent),
        casa_amor_cast=_load_collection(root / "casa_amor_cast", CasaAmorCastContent),
    )


def _load_collection(
    path: Path,
    model: type[ContentT],
) -> dict[str, ContentT]:
    if not path.is_dir():
        return {}
    items: dict[str, ContentT] = {}
    for file in sorted(path.glob("*.md")):
        item = _load_markdown(file, model)
        if item.id in items:
            raise ValueError(f"duplicate content id {item.id!r} in {path}")
        items[item.id] = item
    return items


def _load_markdown(path: Path, model: type[ContentT]) -> ContentT:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"content file missing frontmatter: {path}")
    _, frontmatter, body = text.split("---\n", 2)
    raw = yaml.safe_load(frontmatter)
    if not isinstance(raw, dict):
        raise ValueError(f"content frontmatter must be a mapping: {path}")
    payload = cast(dict[str, object], raw) | {"body": body.strip()}
    return model.model_validate(payload)
