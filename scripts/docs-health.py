"""Structural documentation health checks.

This script checks only changed paths and the path-to-doc ownership map in
``docs/contract-map.yaml``. It intentionally does not inspect prose for words,
phrases, prompt quality, or brand vocabulary.
"""

from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field


class ContractGroup(BaseModel):
    """One source-path group and the docs that own its contract."""

    model_config = ConfigDict(extra="forbid")

    id: str
    paths: list[str] = Field(min_length=1)
    docs: list[str] = Field(min_length=1)


class ContractMap(BaseModel):
    """Validated docs contract map."""

    model_config = ConfigDict(extra="forbid")

    groups: list[ContractGroup]


def main(argv: list[str] | None = None) -> int:
    """Run the docs-health check."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--staged", action="store_true", help="inspect staged files only")
    args = parser.parse_args(argv)
    repo = _repo_root()
    changed = _changed_paths(repo, staged=args.staged)
    if not changed:
        print("docs-health: no changed files")
        return 0
    contract_map = _load_contract_map(repo / "docs" / "contract-map.yaml")
    issues = _contract_issues(contract_map, changed)
    if not issues:
        print(f"docs-health: clean ({len(changed)} changed path(s))")
        return 0
    for issue in issues:
        print(issue)
    return 1


def _contract_issues(contract_map: ContractMap, changed: set[str]) -> list[str]:
    issues: list[str] = []
    for group in contract_map.groups:
        touched = sorted(path for path in changed if _matches_any(path, group.paths))
        if not touched:
            continue
        docs_touched = sorted(path for path in changed if _matches_any(path, group.docs))
        if docs_touched:
            continue
        issues.append(
            f"docs-health: {group.id} changed without owning docs; "
            f"touch one of {group.docs!r} for {touched!r}"
        )
    return issues


def _load_contract_map(path: Path) -> ContractMap:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"contract map must be a mapping: {path}")
    return ContractMap.model_validate(raw)


def _changed_paths(repo: Path, *, staged: bool) -> set[str]:
    commands = [["diff", "--cached", "--name-only"]] if staged else [
        ["diff", "--name-only"],
        ["diff", "--cached", "--name-only"],
        ["ls-files", "--others", "--exclude-standard"],
    ]
    changed: set[str] = set()
    for args in commands:
        output = _git(repo, args)
        changed.update(line.strip().replace("\\", "/") for line in output.splitlines() if line.strip())
    return changed


def _matches_any(path: str, patterns: list[str]) -> bool:
    return any(_matches(path, pattern) for pattern in patterns)


def _matches(path: str, pattern: str) -> bool:
    normalized = pattern.replace("\\", "/")
    if fnmatch.fnmatchcase(path, normalized):
        return True
    if normalized.endswith("/**"):
        return path.startswith(normalized[:-3].rstrip("/") + "/")
    return False


def _repo_root() -> Path:
    output = _git(Path.cwd(), ["rev-parse", "--show-toplevel"])
    if not output:
        raise RuntimeError("not inside a git worktree")
    return Path(output)


def _git(repo: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


if __name__ == "__main__":
    sys.exit(main())
