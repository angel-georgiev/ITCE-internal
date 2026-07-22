"""Command-line entry point: `python -m tracker`."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import diff as diff_mod
from . import emailer, runner, store
from .config_loader import load_stores
from .models import Snapshot
from .report import html as html_report
from .report import markdown as md_report
from .report import terminal as terminal_report
from .report.common import format_eur

DEFAULT_CONFIG = "config/stores.yaml"
DEFAULT_DATA_DIR = "data"


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="tracker",
        description="Track Galaxy Z Flip 7 (256GB) prices across stores delivering to Bulgaria.",
    )
    p.add_argument("--config", default=DEFAULT_CONFIG, help="path to stores.yaml")
    p.add_argument("--data-dir", default=DEFAULT_DATA_DIR, help="where snapshots/reports live")
    p.add_argument("--only", help="comma-separated store ids to include")
    p.add_argument("--skip", help="comma-separated store ids to exclude")
    p.add_argument(
        "--fallback",
        action="store_true",
        help="enable web-search fallback for blocked/empty stores",
    )
    p.add_argument(
        "--format",
        default="terminal,markdown,html",
        help="comma list of terminal,markdown,html",
    )
    p.add_argument("--email", action="store_true", help="email the report if SMTP_* is configured")
    p.add_argument("--no-write", action="store_true", help="don't persist a snapshot (dry run)")
    p.add_argument(
        "--fail-on-empty",
        action="store_true",
        help="exit non-zero if no store returned a price (useful for scheduling)",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="verbose logging")
    return p.parse_args(argv)


def _filter_stores(stores, only: str | None, skip: str | None):
    if only:
        wanted = {s.strip() for s in only.split(",") if s.strip()}
        stores = [s for s in stores if s.id in wanted]
    if skip:
        unwanted = {s.strip() for s in skip.split(",") if s.strip()}
        stores = [s for s in stores if s.id not in unwanted]
    return stores


def _write_reports(snapshot, diff, data_dir: str, formats: set[str]) -> list[Path]:
    written: list[Path] = []
    if not (formats & {"markdown", "html"}):
        return written
    reports_dir = Path(data_dir) / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    date = snapshot.captured_at[:10]
    if "markdown" in formats:
        path = reports_dir / f"report-{date}.md"
        path.write_text(md_report.render(snapshot, diff), encoding="utf-8")
        written.append(path)
    if "html" in formats:
        path = reports_dir / f"report-{date}.html"
        path.write_text(html_report.render(snapshot, diff), encoding="utf-8")
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    formats = {f.strip() for f in args.format.split(",") if f.strip()}

    try:
        stores = _filter_stores(load_stores(args.config), args.only, args.skip)
    except ValueError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2
    if not stores:
        print("no stores selected", file=sys.stderr)
        return 2

    results = runner.run(stores, use_fallback=args.fallback)
    snapshot = Snapshot(captured_at=store.utc_now_iso(), results=results)

    previous = store.find_previous(args.data_dir, snapshot.captured_at)
    diff = diff_mod.compute(snapshot, previous)

    if "terminal" in formats or not formats:
        terminal_report.render(snapshot, diff)

    written = _write_reports(snapshot, diff, args.data_dir, formats)
    for path in written:
        print(f"report written: {path}")

    if not args.no_write:
        saved = store.save(snapshot, args.data_dir)
        print(f"snapshot saved: {saved}")
    else:
        print("dry run: snapshot not saved")

    if args.email:
        subject = "Galaxy Z Flip 7 prices"
        if diff.cheapest is not None:
            subject += f" — cheapest {format_eur(diff.cheapest.price_eur)} at {diff.cheapest.store_name}"
        text = md_report.render(snapshot, diff)
        html = html_report.render(snapshot, diff)
        sent, message = emailer.send(subject, text, html)
        print(message)

    ok_count = len(snapshot.ok_results())
    if args.fail_on_empty and ok_count == 0:
        print("no store returned a price", file=sys.stderr)
        return 1
    return 0
