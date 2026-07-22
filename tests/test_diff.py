from decimal import Decimal

from tracker import diff as diff_mod
from tracker.models import (
    STATUS_BLOCKED,
    STATUS_OK,
    PriceResult,
    Snapshot,
)


def ok(store_id, price, is_agg=False):
    return PriceResult(
        store_id=store_id,
        store_name=store_id.title(),
        status=STATUS_OK,
        url="x",
        price_eur=Decimal(str(price)),
        is_aggregator=is_agg,
    )


def blocked(store_id):
    return PriceResult(
        store_id=store_id, store_name=store_id.title(), status=STATUS_BLOCKED, url="x"
    )


def snap(ts, results):
    return Snapshot(captured_at=ts, results=results)


def test_first_run_has_no_deltas():
    cur = snap("2026-07-22T09:00:00Z", [ok("emag", 990), ok("paz", 900, is_agg=True)])
    d = diff_mod.compute(cur, None)
    assert d.is_first_run
    assert d.cheapest.store_id == "paz"
    assert d.biggest_drop is None


def test_price_drop_and_cheapest():
    prev = snap("2026-07-21T09:00:00Z", [ok("emag", 990), ok("paz", 950)])
    cur = snap("2026-07-22T09:00:00Z", [ok("emag", 999), ok("paz", 900)])
    d = diff_mod.compute(cur, prev)
    assert not d.is_first_run
    assert d.cheapest.store_id == "paz"
    assert d.biggest_drop.store_id == "paz"
    assert d.biggest_drop.delta_eur == Decimal("-50.00")
    kinds = {x.store_id: x.kind for x in d.deltas}
    assert kinds["emag"] == "rose"
    assert kinds["paz"] == "dropped"


def test_cheapest_changed():
    prev = snap("2026-07-21T09:00:00Z", [ok("emag", 900), ok("paz", 950)])
    cur = snap("2026-07-22T09:00:00Z", [ok("emag", 990), ok("paz", 900)])
    d = diff_mod.compute(cur, prev)
    assert d.previous_cheapest_store_id == "emag"
    assert d.cheapest.store_id == "paz"
    assert d.cheapest_changed is True


def test_new_and_lost_listings():
    prev = snap("2026-07-21T09:00:00Z", [ok("emag", 990), blocked("paz")])
    cur = snap("2026-07-22T09:00:00Z", [blocked("emag"), ok("paz", 900)])
    d = diff_mod.compute(cur, prev)
    kinds = {x.store_id: x.kind for x in d.deltas}
    assert kinds["paz"] == "new_listing"    # was blocked, now priced
    assert kinds["emag"] == "lost_listing"  # was priced, now blocked


def test_new_and_removed_store():
    prev = snap("2026-07-21T09:00:00Z", [ok("emag", 990)])
    cur = snap("2026-07-22T09:00:00Z", [ok("emag", 990), ok("newstore", 800)])
    d = diff_mod.compute(cur, prev)
    kinds = {x.store_id: x.kind for x in d.deltas}
    assert kinds["newstore"] == "new_store"

    prev2 = snap("2026-07-21T09:00:00Z", [ok("emag", 990), ok("gone", 800)])
    cur2 = snap("2026-07-22T09:00:00Z", [ok("emag", 990)])
    d2 = diff_mod.compute(cur2, prev2)
    kinds2 = {x.store_id: x.kind for x in d2.deltas}
    assert kinds2["gone"] == "removed_store"


def test_previous_with_zero_ok():
    prev = snap("2026-07-21T09:00:00Z", [blocked("emag"), blocked("paz")])
    cur = snap("2026-07-22T09:00:00Z", [ok("emag", 990), ok("paz", 900)])
    d = diff_mod.compute(cur, prev)
    assert d.cheapest.store_id == "paz"
    assert d.biggest_drop is None  # nothing was priced in both runs
    assert d.cheapest_changed is False  # no previous cheapest to compare


def test_unchanged_price():
    prev = snap("2026-07-21T09:00:00Z", [ok("emag", 990)])
    cur = snap("2026-07-22T09:00:00Z", [ok("emag", 990)])
    d = diff_mod.compute(cur, prev)
    assert d.deltas[0].kind == "unchanged"
    assert d.deltas[0].delta_eur == Decimal("0")
    assert d.biggest_drop is None
