"""M4 box 4 — lib-provided commit-msg hook validator."""

from __future__ import annotations

import json

from devdash.phases.hook import (
    check_commit_message,
    extract_tag,
    install_hook,
    load_phase_keys,
)


def test_extract_tag_both_forms():
    assert extract_tag("[ui] add card") == "ui"
    assert extract_tag("api: add route") == "api"
    assert extract_tag("no tag here") is None


def test_check_commit_message():
    keys = {"ui", "api"}
    assert check_commit_message("[ui] x", keys) == (True, None)
    ok, err = check_commit_message("[zzz] x", keys)
    assert not ok and "unknown phase tag 'zzz'" in err
    ok, err = check_commit_message("no tag", keys)
    assert not ok and "phase tag" in err


def test_check_commit_message_ignores_comments():
    assert check_commit_message("# a comment\n[ui] real subject", {"ui"}) == (True, None)


def test_load_phase_keys_json_shapes(tmp_path):
    list_keys = tmp_path / "a.json"
    list_keys.write_text(json.dumps(["ui", "api"]))
    assert load_phase_keys(list_keys) == {"ui", "api"}

    objs = tmp_path / "b.json"
    objs.write_text(json.dumps({"phases": [{"key": "ui"}, {"key": "api"}]}))
    assert load_phase_keys(objs) == {"ui", "api"}


def test_install_hook_writes_executable(tmp_path):
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    phases = tmp_path / "phases.json"
    phases.write_text(json.dumps(["ui"]))
    hook = install_hook(tmp_path, phases)
    assert hook.exists()
    content = hook.read_text()
    assert "check-commit-msg" in content
    assert hook.stat().st_mode & 0o111  # executable
