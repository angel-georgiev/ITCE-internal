"""Shared presentation helpers so all renderers agree on ordering and text."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ..models import (
    STATUS_OK,
    DiffReport,
    Snapshot,
    StoreDelta,
)

# Order non-ok statuses appear in, after the priced rows.
_STATUS_ORDER = {"unavailable": 0, "blocked": 1, "error": 2}


@dataclass
class Row:
    rank: int | None
    store: str
    price_eur: Decimal | None
    status: str
    delta_eur: Decimal | None
    pct: Decimal | None
    kind: str | None
    is_aggregator: bool
    source: str | None
    tier: str | None
    url: str
    reason: str | None
    color: str | None


def format_eur(value: Decimal | None) -> str:
    if value is None:
        return "—"
    return f"€{value:,.2f}"


def format_delta(delta: Decimal | None, pct: Decimal | None) -> str:
    if delta is None:
        return ""
    if delta == 0:
        return "±0.00"
    arrow = "▼" if delta < 0 else "▲"
    pct_str = f" ({pct:+.1f}%)" if pct is not None else ""
    return f"{arrow} €{abs(delta):,.2f}{pct_str}"


def build_rows(snapshot: Snapshot, diff: DiffReport) -> list[Row]:
    """Priced rows sorted cheapest-first, then non-ok rows grouped by status."""
    delta_by_id = {d.store_id: d for d in diff.deltas}

    ok_rows: list[Row] = []
    other_rows: list[Row] = []
    for r in snapshot.results:
        d = delta_by_id.get(r.store_id)
        row = Row(
            rank=None,
            store=r.store_name,
            price_eur=r.price_eur,
            status=r.status,
            delta_eur=d.delta_eur if d else None,
            pct=d.pct if d else None,
            kind=d.kind if d else None,
            is_aggregator=r.is_aggregator,
            source=r.source,
            tier=r.tier,
            url=r.url,
            reason=r.reason,
            color=r.color,
        )
        if r.status == STATUS_OK and r.price_eur is not None:
            ok_rows.append(row)
        else:
            other_rows.append(row)

    ok_rows.sort(key=lambda x: x.price_eur)
    for i, row in enumerate(ok_rows, start=1):
        row.rank = i
    other_rows.sort(key=lambda x: _STATUS_ORDER.get(x.status, 9))
    return ok_rows + other_rows


def _delta_phrase(d: StoreDelta) -> str:
    return f"{d.store_name} {format_delta(d.delta_eur, d.pct)}"


def summary_lines(snapshot: Snapshot, diff: DiffReport) -> list[str]:
    """Plain-text summary bullets shared across renderers."""
    lines: list[str] = []
    if diff.cheapest is not None:
        agg = " (aggregator)" if diff.cheapest.is_aggregator else ""
        lines.append(
            f"Cheapest now: {format_eur(diff.cheapest.price_eur)} at "
            f"{diff.cheapest.store_name}{agg}"
        )
        if diff.cheapest_changed:
            lines.append("  ↳ the cheapest store changed since the previous run")
    else:
        lines.append("Cheapest now: no store returned a price this run")

    if diff.is_first_run:
        lines.append("Initial baseline saved — deltas will appear from the next run.")
    elif diff.biggest_drop is not None:
        lines.append(f"Biggest drop: {_delta_phrase(diff.biggest_drop)}")
    else:
        lines.append("Biggest drop: no price decreases since the previous run")

    ok = len(snapshot.ok_results())
    total = len(snapshot.results)
    lines.append(f"Coverage: {ok}/{total} stores returned a price")
    return lines
