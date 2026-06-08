"""M4 box 2 — phase taxonomy as host config + phases REST routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from devdash import DevDashConfig, PhaseSpec, PhaseTrackerConfig, make_dashboard_app
from devdash.db import dispose_engine, make_engine
from devdash.phases.repository import list_phases, seed_phases
from devdash.phases.taxonomy import ModelRate, PriceTable

SAMPLE = PhaseTrackerConfig(
    phases=[
        PhaseSpec(
            key="ui",
            label="UI",
            status="in_progress",
            complexity=5,
            display_order=1,
            color="#abc",
        ),
        PhaseSpec(key="api", label="API", display_order=2),
    ]
)


def test_taxonomy_from_dict():
    cfg = PhaseTrackerConfig.from_dict({"phases": [{"key": "x", "label": "X"}]})
    assert cfg.phases[0].key == "x"


def test_price_table_unknown_model_is_none():
    pt = PriceTable(rates={"m": ModelRate(input=3.0, output=15.0)})
    assert pt.cost("m", input_tokens=1_000_000) == 3.0
    assert pt.cost("absent", input_tokens=1_000_000) is None  # unknown -> None (D08)


async def test_seed_is_idempotent_and_non_destructive(tmp_path):
    url = f"sqlite+aiosqlite:///{tmp_path / 'p.db'}"
    engine = make_engine(url)
    from devdash.migrations import migrate

    await migrate(engine, DevDashConfig(database_url=url))
    assert await seed_phases(engine, SAMPLE.phases) == 2
    assert await seed_phases(engine, SAMPLE.phases) == 0  # already present
    rows = {r["phase"]: r for r in await list_phases(engine)}
    assert set(rows) == {"ui", "api"}
    assert rows["ui"]["status"] == "in_progress"
    await dispose_engine(engine)


@pytest.fixture
def client(tmp_path):
    config = DevDashConfig(database_url=f"sqlite+aiosqlite:///{tmp_path / 'app.db'}")
    app = make_dashboard_app(config, phases_config=SAMPLE)
    with TestClient(app) as c:
        yield c


def test_get_phases_includes_taxonomy_color(client):
    rows = client.get("/dev/phases/phases").json()
    by = {r["phase"]: r for r in rows}
    assert by["ui"]["color"] == "#abc"
    assert by["ui"]["label"] == "UI"
    assert [r["phase"] for r in rows] == ["ui", "api"]  # display_order


def test_session_crud(client):
    created = client.post(
        "/dev/phases/sessions",
        json={
            "dev_name": "ada",
            "started_at": "2026-06-08T00:00:00Z",
            "ended_at": "2026-06-08T01:00:00Z",
            "duration_sec": 3600,
            "phase": "ui",
        },
    )
    assert created.status_code == 201
    sid = created.json()["id"]

    listed = client.get("/dev/phases/sessions").json()
    assert any(s["id"] == sid for s in listed)

    updated = client.put(f"/dev/phases/sessions/{sid}", json={"notes": "tweak"})
    assert updated.status_code == 200
    assert updated.json()["notes"] == "tweak"

    assert client.delete(f"/dev/phases/sessions/{sid}").status_code == 204
    assert client.delete(f"/dev/phases/sessions/{sid}").status_code == 404
