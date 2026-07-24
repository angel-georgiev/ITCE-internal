"""Terminal renderer — rich table if available, else plain fixed-width text."""

from __future__ import annotations

from ..models import DiffReport, Snapshot
from .common import build_rows, format_delta, format_eur, summary_lines


def _plain(snapshot: Snapshot, diff: DiffReport) -> str:
    rows = build_rows(snapshot, diff)
    out = ["Galaxy Z Flip 7 (256GB) — prices delivering to Bulgaria", ""]
    out += summary_lines(snapshot, diff)
    out.append("")
    header = f"{'#':>2}  {'Store':<22}{'Price':>12}  {'Δ vs prev':<20}{'Src':<8}Status"
    out.append(header)
    out.append("-" * len(header))
    for r in rows:
        rank = str(r.rank) if r.rank else ""
        store = r.store + (" *" if r.is_aggregator else "")
        price = format_eur(r.price_eur)
        delta = format_delta(r.delta_eur, r.pct)
        src = (r.tier or r.source or "")
        if r.status == "ok":
            status = "⚠ verify" if r.verify_note else ""
        else:
            status = r.status
        line = f"{rank:>2}  {store:<22}{price:>12}  {delta:<20}{src:<8}{status}"
        out.append(line)
        if r.status != "ok" and r.reason:
            out.append(f"      ↳ {r.reason}")
        elif r.verify_note:
            out.append(f"      ↳ {r.verify_note}")
    out.append("")
    out.append("* = price aggregator (links to third-party sellers)")
    return "\n".join(out)


def render(snapshot: Snapshot, diff: DiffReport) -> None:
    """Print the run to stdout."""
    try:
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        print(_plain(snapshot, diff))
        return

    console = Console()
    console.rule("[bold]Galaxy Z Flip 7 (256GB) — prices delivering to Bulgaria")
    for line in summary_lines(snapshot, diff):
        console.print(line)

    table = Table(show_lines=False, expand=False)
    table.add_column("#", justify="right", style="dim")
    table.add_column("Store")
    table.add_column("Price", justify="right")
    table.add_column("Δ vs prev")
    table.add_column("Src", style="dim")
    table.add_column("Status")

    for r in build_rows(snapshot, diff):
        store = r.store + (" [dim]*[/dim]" if r.is_aggregator else "")
        delta = format_delta(r.delta_eur, r.pct)
        if r.delta_eur is not None and r.delta_eur < 0:
            delta = f"[green]{delta}[/green]"
        elif r.delta_eur is not None and r.delta_eur > 0:
            delta = f"[red]{delta}[/red]"
        if r.status == "ok":
            status = f"[red]⚠ verify[/red] [dim]{r.verify_note}[/dim]" if r.verify_note else ""
        else:
            status = f"[yellow]{r.status}[/yellow]"
        table.add_row(
            str(r.rank) if r.rank else "",
            store,
            format_eur(r.price_eur),
            delta,
            r.tier or r.source or "",
            status,
        )
    console.print(table)
    console.print("[dim]* = price aggregator (links to third-party sellers)[/dim]")
