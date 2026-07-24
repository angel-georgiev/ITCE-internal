"""Self-contained HTML report renderer (inline CSS, emailable as-is)."""

from __future__ import annotations

from html import escape

from ..models import DiffReport, Snapshot
from .common import build_rows, format_delta, format_eur, summary_lines

_STYLE = """
body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
  color:#1a1a1a;background:#fff;margin:0;padding:24px;}
h1{font-size:20px;margin:0 0 4px;}
.meta{color:#666;font-size:13px;margin-bottom:16px;}
.summary{background:#f5f7fa;border:1px solid #e2e8f0;border-radius:8px;
  padding:12px 16px;margin-bottom:20px;}
.summary li{margin:2px 0;}
table{border-collapse:collapse;width:100%;font-size:14px;}
th,td{padding:8px 10px;border-bottom:1px solid #eee;text-align:left;}
th{background:#fafafa;font-weight:600;}
td.num,th.num{text-align:right;}
tr.cheapest{background:#eafaf0;}
.drop{color:#137333;font-weight:600;}
.rise{color:#c5221f;font-weight:600;}
.status{color:#b7791f;font-weight:600;}
.verify{color:#c5221f;font-weight:600;}
.agg{color:#888;}
.note{color:#999;font-size:12px;}
td.link{max-width:320px;}
td.link a{color:#1a73e8;word-break:break-all;font-size:12px;}
@media(prefers-color-scheme:dark){
  body{background:#111;color:#eee;}
  .summary{background:#1b1e24;border-color:#333;}
  th{background:#1b1e24;}th,td{border-color:#2a2a2a;}
  tr.cheapest{background:#12301f;}
}
"""


def render(snapshot: Snapshot, diff: DiffReport) -> str:
    rows = build_rows(snapshot, diff)
    summary = "".join(f"<li>{escape(s.strip())}</li>" for s in summary_lines(snapshot, diff))

    body_rows = []
    for r in rows:
        cls = "cheapest" if r.rank == 1 else ""
        store = escape(r.store) + (" <span class='agg'>*</span>" if r.is_aggregator else "")
        if r.status == "ok" and r.url:
            store = f"<a href='{escape(r.url)}'>{store}</a>"
        delta_txt = format_delta(r.delta_eur, r.pct)
        if r.delta_eur is not None and r.delta_eur < 0:
            delta_html = f"<span class='drop'>{escape(delta_txt)}</span>"
        elif r.delta_eur is not None and r.delta_eur > 0:
            delta_html = f"<span class='rise'>{escape(delta_txt)}</span>"
        else:
            delta_html = escape(delta_txt)
        if r.status == "ok":
            if r.verify_note:
                status_html = f"<span class='verify'>⚠ verify</span> <span class='note'>{escape(r.verify_note)}</span>"
            else:
                status_html = "ok"
        else:
            note = f" <span class='note'>{escape(r.reason)}</span>" if r.reason else ""
            status_html = f"<span class='status'>{escape(r.status)}</span>{note}"
        link_html = (
            f"<a href='{escape(r.url)}'>{escape(r.url)}</a>" if r.url else ""
        )
        body_rows.append(
            f"<tr class='{cls}'><td class='num'>{r.rank or ''}</td><td>{store}</td>"
            f"<td class='num'>{escape(format_eur(r.price_eur))}</td><td>{delta_html}</td>"
            f"<td>{escape(r.tier or r.source or '')}</td><td>{status_html}</td>"
            f"<td class='link'>{link_html}</td></tr>"
        )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Galaxy Z Flip 7 price tracker</title>
<style>{_STYLE}</style></head>
<body>
<h1>Galaxy Z Flip 7 (256GB) — prices delivering to Bulgaria</h1>
<div class="meta">Captured {escape(snapshot.captured_at)} · normalized to EUR
 (1 EUR = {snapshot.bgn_per_eur} BGN)</div>
<div class="summary"><ul>{summary}</ul></div>
<table>
<thead><tr><th class="num">#</th><th>Store</th><th class="num">Price (EUR)</th>
<th>Δ vs previous</th><th>Source</th><th>Status</th><th>Link</th></tr></thead>
<tbody>{''.join(body_rows)}</tbody>
</table>
<p class="note">* = price aggregator (links to third-party sellers)</p>
</body></html>"""
