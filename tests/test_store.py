from decimal import Decimal

from tracker import store
from tracker.models import STATUS_OK, PriceResult, Snapshot


def make(ts):
    return Snapshot(
        captured_at=ts,
        results=[
            PriceResult(
                store_id="emag", store_name="eMAG", status=STATUS_OK, url="x",
                price_eur=Decimal("989.90"),
            )
        ],
    )


def test_save_and_load_roundtrip(tmp_path):
    snap = make("2026-07-22T09:00:00Z")
    path = store.save(snap, tmp_path)
    assert path.exists()
    loaded = store.load_all(tmp_path)
    assert len(loaded) == 1
    assert loaded[0].results[0].price_eur == Decimal("989.90")


def test_find_previous_picks_most_recent_older(tmp_path):
    store.save(make("2026-07-20T09:00:00Z"), tmp_path)
    store.save(make("2026-07-21T09:00:00Z"), tmp_path)
    store.save(make("2026-07-22T09:00:00Z"), tmp_path)
    prev = store.find_previous(tmp_path, "2026-07-22T09:00:00Z")
    assert prev.captured_at == "2026-07-21T09:00:00Z"


def test_find_previous_tolerates_gaps(tmp_path):
    # Skipped days: only two snapshots a week apart.
    store.save(make("2026-07-15T09:00:00Z"), tmp_path)
    store.save(make("2026-07-22T09:00:00Z"), tmp_path)
    prev = store.find_previous(tmp_path, "2026-07-22T09:00:00Z")
    assert prev.captured_at == "2026-07-15T09:00:00Z"


def test_find_previous_none_on_first_run(tmp_path):
    store.save(make("2026-07-22T09:00:00Z"), tmp_path)
    assert store.find_previous(tmp_path, "2026-07-22T09:00:00Z") is None


def test_find_previous_ignores_current_file(tmp_path):
    # A snapshot with the same timestamp must not count as its own previous.
    store.save(make("2026-07-22T09:00:00Z"), tmp_path)
    assert store.find_previous(tmp_path, "2026-07-22T09:00:00Z") is None
