"""Markdown report renderer."""

from __future__ import annotations

from ..models import DiffReport, Snapshot
from .common import build_rows, format_delta, format_eur, summary_lines


def render(snapshot: Snapshot, diff: DiffReport) -> str:
    rows = build_rows(snapshot, diff)
    lines = [
        "# Galaxy Z Flip 7 (256GB) — prices delivering to Bulgaria",
        "",
        f"_Captured: {snapshot.captured_at} · prices normalized to EUR "
        f"(1 EUR = {snapshot.bgn_per_eur} BGN)_",
        "",
        "## Summary",
        "",
    ]
    lines += [f"- {line.strip()}" for line in summary_lines(snapshot, diff)]
    lines += [
        "",
        "## Prices",
        "",
        "| # | Store | Price (EUR) | Δ vs previous | Source | Status | Link |",
        "|---:|---|---:|---|---|---|---|",
    ]
    for r in rows:
        store = r.store + (" \\*" if r.is_aggregator else "")
        if r.status == "ok" and r.url:
            store = f"[{store}]({r.url})"
        rank = str(r.rank) if r.rank else ""
        if r.status == "ok":
            status = f"⚠ verify — {r.verify_note}" if r.verify_note else "ok"
        else:
            status = f"**{r.status}**"
        delta = format_delta(r.delta_eur, r.pct) or "—"
        note = f" — {r.reason}" if r.status != "ok" and r.reason else ""
        # Full product URL as an autolink so it is visible and clickable in the file.
        link = f"<{r.url}>" if r.url else ""
        lines.append(
            f"| {rank} | {store} | {format_eur(r.price_eur)} | {delta} "
            f"| {r.tier or r.source or ''} | {status}{note} | {link} |"
        )
    lines += ["", "\\* = price aggregator (links to third-party sellers)", ""]
    return "\n".join(lines)
