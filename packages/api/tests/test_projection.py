"""M4 box 4 — projection (optional, method:'none') + degraded manual mode."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from devdash import DevDashConfig, PhaseSpec, PhaseTrackerConfig, make_dashboard_app
from devdash.phases.projection import compute_projection

TODAY = date(2026, 6, 8)


def test_projection_none_without_complexity():
    res = compute_projection(
        [{"status": "pending"}], cumulative_sec=100, elapsed_days=1, today=TODAY
    )
    assert res.method == "none" and res.projected_finish_date is None


def test_projection_naive_when_nothing_done():
    res = compute_projection(
        [{"complexity": 3, "status": "pending"}], cumulative_sec=100, elapsed_days=1, today=TODAY
    )
    assert res.method == "naive" and res.projected_finish_date is None


def test_projection_calibrated():
    res = compute_projection(
        [
            {"complexity": 2, "status": "done"},
            {"complexity": 2, "status": "pending"},
        ],
        cumulative_sec=3600,
        elapsed_days=1,
        today=TODAY,
    )
    assert res.method == "calibrated"
    assert res.target_sec == 7200
    assert res.remaining_sec == 3600
    assert res.projected_finish_date == (TODAY + timedelta(days=1)).isoformat()


def test_manual_session_mode_no_taxonomy(tmp_path):
    # No phases supplied -> manual sessions still work; projection is 'none'.
    config = DevDashConfig(database_url=f"sqlite+aiosqlite:///{tmp_path / 'm.db'}")
    app = make_dashboard_app(config, phases_config=PhaseTrackerConfig())
    with TestClient(app) as c:
        created = c.post(
            "/dev/phases/sessions",
            json={
                "dev_name": "ada",
                "started_at": "2026-06-08T00:00:00Z",
                "ended_at": "2026-06-08T01:00:00Z",
                "duration_sec": 3600,
            },
        )
        assert created.status_code == 201
        assert c.get("/dev/phases/projection").json()["method"] == "none"


def test_projection_route_calibrated(tmp_path):
    config = DevDashConfig(database_url=f"sqlite+aiosqlite:///{tmp_path / 'p.db'}")
    taxonomy = PhaseTrackerConfig(
        phases=[
            PhaseSpec(key="a", complexity=1, status="done"),
            PhaseSpec(key="b", complexity=1, status="pending"),
        ]
    )
    app = make_dashboard_app(config, phases_config=taxonomy)
    with TestClient(app) as c:
        c.post(
            "/dev/phases/sessions",
            json={
                "dev_name": "ada",
                "started_at": "2026-06-08T00:00:00Z",
                "ended_at": "2026-06-08T02:00:00Z",
                "duration_sec": 7200,
                "phase": "a",
            },
        )
        proj = c.get("/dev/phases/projection").json()
        assert proj["method"] == "calibrated"
        assert proj["remaining_sec"] == 7200  # half done -> equal remaining
