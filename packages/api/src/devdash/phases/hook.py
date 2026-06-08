"""Generic commit-msg validation: a commit's tag prefix must be a known phase.

devdash ships the validator + the git hook installer; the *allowed keys* are
host content (the host's phase taxonomy). Kept dependency-light: phase keys load
from a JSON or YAML file (YAML only if PyYAML is importable).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .taxonomy import DEFAULT_TAG_REGEX


def extract_tag(message: str, tag_regex: str = DEFAULT_TAG_REGEX) -> str | None:
    m = re.match(tag_regex, message.strip())
    if not m:
        return None
    return next((g for g in m.groups() if g), None)


def check_commit_message(
    message: str, allowed_keys: set[str], tag_regex: str = DEFAULT_TAG_REGEX
) -> tuple[bool, str | None]:
    # Ignore comment lines / empty messages (e.g. merge templates).
    subject = next(
        (ln for ln in message.splitlines() if ln.strip() and not ln.startswith("#")), ""
    )
    tag = extract_tag(subject, tag_regex)
    if tag is None:
        return False, "commit subject must start with a phase tag, e.g. '[ui] ...' or 'ui: ...'"
    if tag not in allowed_keys:
        return False, f"unknown phase tag '{tag}'. Allowed: {', '.join(sorted(allowed_keys))}"
    return True, None


def load_phase_keys(path: str | Path) -> set[str]:
    """Load the allowed phase keys from a JSON/YAML file.

    Accepts a list of keys, a list of {key: ...} objects, or a
    PhaseTrackerConfig-shaped dict with a `phases` list.
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    data: object
    if p.suffix in {".yml", ".yaml"}:
        try:
            import yaml  # optional
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise RuntimeError("PyYAML required to read a YAML phases file") from exc
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)

    items = data.get("phases", data) if isinstance(data, dict) else data
    keys: set[str] = set()
    if isinstance(items, list):
        for item in items:
            if isinstance(item, str):
                keys.add(item)
            elif isinstance(item, dict) and "key" in item:
                keys.add(str(item["key"]))
    return keys


HOOK_TEMPLATE = """#!/usr/bin/env bash
# devdash commit-msg hook — validates the phase tag against the host taxonomy.
exec python -m devdash check-commit-msg "$1" --phases-file {phases_file}
"""


def install_hook(repo: str | Path, phases_file: str | Path) -> Path:
    hook = Path(repo) / ".git" / "hooks" / "commit-msg"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(HOOK_TEMPLATE.format(phases_file=Path(phases_file).resolve()))
    hook.chmod(0o755)
    return hook
