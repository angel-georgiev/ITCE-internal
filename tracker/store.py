"""Snapshot persistence.

Each run writes one JSON file under <data_dir>/snapshots/. The "previous"
snapshot is the most recent file strictly older than the current one, so
skipped days need no special handling.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import Snapshot


def utc_now_iso() -> str:
    """Current UTC time as an ISO-8601 string (seconds precision, Z suffix)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _filename_stem(captured_at: str) -> str:
    """Filesystem-safe, lexically-sortable filename stem from an ISO timestamp."""
    return captured_at.replace(":", "-")


def snapshots_dir(data_dir: str | Path) -> Path:
    return Path(data_dir) / "snapshots"


def save(snapshot: Snapshot, data_dir: str | Path) -> Path:
    """Write the snapshot to <data_dir>/snapshots/<timestamp>.json."""
    directory = snapshots_dir(data_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{_filename_stem(snapshot.captured_at)}.json"
    path.write_text(
        json.dumps(snapshot.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def _load(path: Path) -> Snapshot | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Snapshot.from_dict(data)
    except (json.JSONDecodeError, KeyError, OSError):
        return None


def load_all(data_dir: str | Path) -> list[Snapshot]:
    """All snapshots, sorted oldest-first by captured_at."""
    directory = snapshots_dir(data_dir)
    if not directory.exists():
        return []
    snaps = [s for p in sorted(directory.glob("*.json")) if (s := _load(p)) is not None]
    snaps.sort(key=lambda s: s.captured_at)
    return snaps


def find_previous(data_dir: str | Path, current_captured_at: str) -> Snapshot | None:
    """Most recent snapshot strictly older than current_captured_at."""
    older = [s for s in load_all(data_dir) if s.captured_at < current_captured_at]
    return older[-1] if older else None
