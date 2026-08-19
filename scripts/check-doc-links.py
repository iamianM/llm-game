"""Validate local links in current Markdown documentation."""

from __future__ import annotations

import re
import sys
from pathlib import Path

MARKDOWN_TARGET = re.compile(r"!?\[[^\]]*\]\((?P<target>[^)]+)\)")
HTML_TARGET = re.compile(r'(?:src|href)="(?P<target>[^"]+)"')
IGNORED_PARTS = {".git", ".venv", "node_modules", "review-packet"}


def main() -> int:
    """Report local links that do not resolve from their owning document."""
    repo = Path(__file__).resolve().parents[1]
    issues: list[str] = []
    for path in sorted(repo.rglob("*.md")):
        relative = path.relative_to(repo)
        if _ignored(relative):
            continue
        text = path.read_text(encoding="utf-8")
        targets = [match.group("target") for match in MARKDOWN_TARGET.finditer(text)]
        targets.extend(match.group("target") for match in HTML_TARGET.finditer(text))
        for raw_target in targets:
            target = _path_target(raw_target)
            if target is None:
                continue
            resolved = target if target.is_absolute() else path.parent / target
            if not resolved.exists():
                issues.append(f"{relative.as_posix()}: {raw_target}")

    if issues:
        print("doc-links: unresolved local targets")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("doc-links: clean")
    return 0


def _ignored(relative: Path) -> bool:
    parts = set(relative.parts)
    if parts & IGNORED_PARTS:
        return True
    return relative.parts[:2] == ("docs", "archive")


def _path_target(raw_target: str) -> Path | None:
    target = raw_target.strip().strip("<>")
    if target.startswith(("http://", "https://", "mailto:", "data:", "#")):
        return None
    target = target.split("#", 1)[0]
    if not target:
        return None
    if " " in target and not raw_target.strip().startswith("<"):
        target = target.split(" ", 1)[0]
    return Path(target)


if __name__ == "__main__":
    sys.exit(main())
