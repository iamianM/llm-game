"""SSE formatting helpers."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator


def sse(event: str, data: object, *, event_id: int | None = None) -> str:
    """Format one SSE event."""
    prefix = "" if event_id is None else f"id: {event_id}\n"
    return f"{prefix}event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def chunk_text(text: str, *, size: int = 18) -> AsyncIterator[str]:
    """Yield small text chunks for the browser typewriter."""
    if not text:
        return
    for index in range(0, len(text), size):
        await asyncio.sleep(0.005)
        yield text[index : index + size]
