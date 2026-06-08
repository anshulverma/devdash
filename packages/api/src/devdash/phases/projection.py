"""Complexity-weighted finish-date / burn-rate projection.

Optional: when the host taxonomy carries no complexity, projection degrades to
``method='none'`` and the UI hides the finish-date card (burn-rate over time
still renders). When complexity exists but nothing is done yet, it cannot
calibrate a finish date → ``method='naive'``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class ProjectionResult:
    method: str  # 'calibrated' | 'naive' | 'none'
    cumulative_sec: int
    remaining_sec: int
    target_sec: int
    burn_per_day_sec: float | None
    projected_finish_date: str | None


def compute_projection(
    phases: list[dict],
    *,
    cumulative_sec: int,
    elapsed_days: float,
    today: date,
) -> ProjectionResult:
    """Project remaining time from complexity-weighted progress.

    `phases` rows carry optional `complexity` and a `status`; `cumulative_sec` is
    total tracked time; `elapsed_days` is the wall-clock span of that work.
    """
    has_complexity = any((p.get("complexity") or 0) > 0 for p in phases)
    if not has_complexity:
        return ProjectionResult("none", cumulative_sec, 0, cumulative_sec, None, None)

    total_cx = sum((p.get("complexity") or 0) for p in phases)
    done_cx = sum((p.get("complexity") or 0) for p in phases if p.get("status") == "done")
    burn = cumulative_sec / elapsed_days if elapsed_days > 0 else None

    if done_cx <= 0 or total_cx <= 0:
        # Complexity exists but nothing done — can't calibrate a finish date.
        return ProjectionResult("naive", cumulative_sec, 0, cumulative_sec, burn, None)

    fraction_done = done_cx / total_cx
    target_sec = int(cumulative_sec / fraction_done)
    remaining_sec = max(0, target_sec - cumulative_sec)
    finish = None
    if burn and burn > 0:
        days_left = remaining_sec / burn
        finish = (today + timedelta(days=days_left)).isoformat()
    return ProjectionResult(
        "calibrated", cumulative_sec, remaining_sec, target_sec, burn, finish
    )
