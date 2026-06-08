"""Claude Code `~/.claude` JSONL transcript importer.

One adapter that produces the provider-neutral TokenRow contract. The engine
knows nothing about `~/.claude`; this parser does. Pure-stdlib (no extra deps).
"""

from __future__ import annotations

import glob
import json
import os
from collections.abc import Iterable

from ..phases.tokens import TokenRow


def parse_lines(lines: Iterable[str], *, dev_name: str) -> list[TokenRow]:
    """Parse Claude Code transcript JSONL lines into TokenRows (usage rows only)."""
    rows: list[TokenRow] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = obj.get("message") or {}
        usage = message.get("usage")
        uuid = obj.get("uuid") or message.get("id")
        ts = obj.get("timestamp")
        if not usage or not uuid or not ts:
            continue
        rows.append(
            TokenRow(
                message_uuid=str(uuid),
                ts=str(ts),
                model=message.get("model", "unknown"),
                dev_name=dev_name,
                provider="anthropic",
                input_tokens=int(usage.get("input_tokens", 0) or 0),
                output_tokens=int(usage.get("output_tokens", 0) or 0),
                cache_read_tokens=int(usage.get("cache_read_input_tokens", 0) or 0),
                cache_creation_tokens=int(usage.get("cache_creation_input_tokens", 0) or 0),
            )
        )
    return rows


def parse_files(paths: Iterable[str], *, dev_name: str) -> list[TokenRow]:
    rows: list[TokenRow] = []
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            rows.extend(parse_lines(fh, dev_name=dev_name))
    return rows


def default_transcript_glob() -> str:
    return os.path.expanduser("~/.claude/**/*.jsonl")


def discover(dev_name: str, pattern: str | None = None) -> list[TokenRow]:
    paths = glob.glob(pattern or default_transcript_glob(), recursive=True)
    return parse_files(paths, dev_name=dev_name)
