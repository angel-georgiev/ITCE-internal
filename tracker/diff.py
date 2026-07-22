"""Diff engine: compare the current run against the previous run.

Pure functions over Snapshot objects — no I/O.
"""

from __future__ import annotations

from decimal import Decimal

from .models import (
    STATUS_OK,
    DiffReport,
    PriceResult,
    Snapshot,
    StoreDelta,
)


def _is_ok(r: PriceResult | None) -> bool:
    return r is not None and r.status == STATUS_OK and r.price_eur is not None


def _by_id(snapshot: Snapshot | None) -> dict[str, PriceResult]:
    if snapshot is None:
        return {}
    return {r.store_id: r for r in snapshot.results}


def _classify(cur: PriceResult | None, prev: PriceResult | None) -> StoreDelta:
    store = cur or prev
    assert store is not None
    is_agg = store.is_aggregator

    cur_ok = _is_ok(cur)
    prev_ok = _is_ok(prev)

    if cur_ok and prev_ok:
        delta = cur.price_eur - prev.price_eur
        pct = (delta / prev.price_eur * Decimal(100)) if prev.price_eur else None
        if delta < 0:
            kind = "dropped"
        elif delta > 0:
            kind = "rose"
        else:
            kind = "unchanged"
        return StoreDelta(
            store_id=store.store_id,
            store_name=store.store_name,
            kind=kind,
            current_eur=cur.price_eur,
            previous_eur=prev.price_eur,
            delta_eur=delta,
            pct=pct,
            is_aggregator=is_agg,
        )

    if cur_ok and not prev_ok:
        # New price where there wasn't one (new store, or recovered listing).
        kind = "new_store" if prev is None else "new_listing"
        return StoreDelta(
            store_id=store.store_id,
            store_name=store.store_name,
            kind=kind,
            current_eur=cur.price_eur,
            is_aggregator=is_agg,
        )

    if prev_ok and not cur_ok:
        # Had a price before, don't now (blocked/unavailable/removed).
        kind = "removed_store" if cur is None else "lost_listing"
        return StoreDelta(
            store_id=store.store_id,
            store_name=store.store_name,
            kind=kind,
            previous_eur=prev.price_eur,
            is_aggregator=is_agg,
        )

    # Neither run had a usable price.
    return StoreDelta(
        store_id=store.store_id,
        store_name=store.store_name,
        kind="unchanged",
        is_aggregator=is_agg,
    )


def cheapest_of(snapshot: Snapshot, *, include_aggregators: bool = True) -> PriceResult | None:
    """Cheapest OK result in a snapshot, or None."""
    candidates = [
        r
        for r in snapshot.ok_results()
        if include_aggregators or not r.is_aggregator
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda r: r.price_eur)


def compute(current: Snapshot, previous: Snapshot | None) -> DiffReport:
    """Build a DiffReport for the current run relative to the previous run."""
    cur_map = _by_id(current)
    prev_map = _by_id(previous)

    store_ids = list(cur_map.keys())
    for sid in prev_map:
        if sid not in cur_map:
            store_ids.append(sid)

    deltas = [_classify(cur_map.get(sid), prev_map.get(sid)) for sid in store_ids]

    cheapest = cheapest_of(current)
    prev_cheapest = cheapest_of(previous) if previous is not None else None
    prev_cheapest_id = prev_cheapest.store_id if prev_cheapest else None
    cheapest_changed = bool(
        previous is not None
        and cheapest is not None
        and prev_cheapest_id is not None
        and cheapest.store_id != prev_cheapest_id
    )

    # Biggest absolute and percentage drops among stores OK in both runs.
    drops = [d for d in deltas if d.kind == "dropped" and d.delta_eur is not None]
    biggest_drop = min(drops, key=lambda d: d.delta_eur) if drops else None
    biggest_pct_drop = (
        min([d for d in drops if d.pct is not None], key=lambda d: d.pct)
        if any(d.pct is not None for d in drops)
        else None
    )

    return DiffReport(
        is_first_run=previous is None,
        deltas=deltas,
        cheapest=cheapest,
        previous_cheapest_store_id=prev_cheapest_id,
        cheapest_changed=cheapest_changed,
        biggest_drop=biggest_drop,
        biggest_pct_drop=biggest_pct_drop,
    )
