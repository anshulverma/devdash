"""M4 box 3 — provider-neutral token ingest + claude-code importer (D08)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from devdash import DevDashConfig, PhaseTrackerConfig, make_dashboard_app
from devdash.importers import claude_code
from devdash.phases.taxonomy import ModelRate, PriceTable

SAMPLE_JSONL = "\n".join(
    [
        '{"type":"assistant","uuid":"abc","timestamp":"2026-06-08T00:00:00Z",'
        '"message":{"model":"claude-opus","usage":{"input_tokens":10,"output_tokens":20,'
        '"cache_read_input_tokens":5,"cache_creation_input_tokens":2}}}',
        '{"type":"user","uuid":"def","timestamp":"2026-06-08T00:01:00Z","message":{"content":"hi"}}',
        "not json at all",
    ]
)


def test_claude_code_parser():
    rows = claude_code.parse_lines(SAMPLE_JSONL.splitlines(), dev_name="ada")
    assert len(rows) == 1  # only the usage row
    r = rows[0]
    assert r.message_uuid == "abc"
    assert r.model == "claude-opus"
    assert r.provider == "anthropic"
    assert (r.input_tokens, r.output_tokens, r.cache_read_tokens, r.cache_creation_tokens) == (
        10,
        20,
        5,
        2,
    )


@pytest.fixture
def client(tmp_path):
    config = DevDashConfig(database_url=f"sqlite+aiosqlite:///{tmp_path / 'tok.db'}")
    prices = PriceTable(rates={"known": ModelRate(input=3.0, output=15.0)})
    app = make_dashboard_app(config, phases_config=PhaseTrackerConfig(prices=prices))
    with TestClient(app) as c:
        yield c


def _row(uuid: str, model: str, **tok):
    return {
        "message_uuid": uuid,
        "ts": "2026-06-08T00:00:00Z",
        "model": model,
        "dev_name": "ada",
        **tok,
    }


def test_import_computes_cost_from_price_table(client):
    res = client.post(
        "/dev/phases/tokens/import",
        json=[_row("u1", "known", input_tokens=1_000_000, output_tokens=1_000_000)],
    ).json()
    assert res["imported"] == 1 and res["unknown_models"] == []
    stats = client.get("/dev/phases/tokens/stats").json()
    assert stats["cost_usd"] == pytest.approx(18.0)  # 1M*3 + 1M*15, /1M


def test_unknown_model_costs_zero_and_warns(client):
    res = client.post(
        "/dev/phases/tokens/import", json=[_row("u2", "mystery", input_tokens=1000)]
    ).json()
    assert res["imported"] == 1
    assert res["unknown_models"] == ["mystery"]
    assert client.get("/dev/phases/tokens/stats").json()["by_model"]["mystery"] == 0.0


def test_import_is_idempotent_on_message_uuid(client):
    client.post("/dev/phases/tokens/import", json=[_row("dup", "known", input_tokens=10)])
    res = client.post(
        "/dev/phases/tokens/import", json=[_row("dup", "known", input_tokens=10)]
    ).json()
    assert res["imported"] == 0 and res["skipped"] == 1
