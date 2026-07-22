# Galaxy Z Flip 7 price tracker (Bulgaria)

Tracks the price of the **Samsung Galaxy Z Flip 7 (256GB)** across online stores
that deliver to Bulgaria, prints the options **sorted by price**, and remembers
history so each run highlights **what changed since the previous run** — the
**biggest drop** and the **current cheapest**.

Runs manually today (one command); built to be put on a daily schedule later.

## Quick start

```bash
pip install -r requirements.txt      # Playwright uses a pre-installed Chromium
python -m tracker                    # scrape, print table, write reports, save snapshot
```

First cut tracks two stores — **pazaruvaj.com** (a BG price aggregator) and
**eMAG.bg** (the biggest BG e-commerce site). Add more by editing
`config/stores.yaml` (see below) — no code changes needed.

## What a run does

1. Fetches each enabled store in `config/stores.yaml`.
2. Normalizes every price to **EUR** (product price only; Bulgaria adopted the
   euro in Jan 2026, and any leftover BGN is converted at the fixed rate
   `1 EUR = 1.95583 BGN`).
3. Prints a table sorted cheapest-first, writes `data/reports/report-<date>.{md,html}`.
4. Saves a snapshot to `data/snapshots/<timestamp>.json` and diffs it against the
   most-recent previous snapshot (skipped days are fine — it compares against the
   last run, whenever that was).

### Fetching is best-effort and escalates per store

For each store (`fetch: auto`):

1. **HTTP** (`requests`) — fast path. Requests are sent with browser-like
   headers, advertising only the response encodings the environment can
   actually decode (`gzip`/`deflate`, plus `br` when the optional `brotli`
   package is installed) so a store's compressed page is never left as
   undecodable bytes.
2. **Headless browser** (Playwright/Chromium) — if HTTP is blocked (Cloudflare,
   etc.) or the price isn't in the static HTML, the page is rendered in a real
   browser and scraped from the DOM.
3. **Web search** (`--fallback`, optional) — last-resort discovery/verification.

A store that fails all tiers is marked `unavailable`/`blocked` **with a reason**
and the run continues — one broken store never aborts the run.

## CLI

```
python -m tracker [options]
  --config PATH        stores config (default: config/stores.yaml)
  --data-dir PATH      snapshots + reports live here (default: data/)
  --only a,b           only these store ids
  --skip a,b           exclude these store ids
  --fallback           enable the web-search fallback tier
  --format ...         comma list of terminal,markdown,html (default: all)
  --email              email the report if SMTP_* env vars are set (see below)
  --no-write           dry run: don't persist a snapshot
  --fail-on-empty      exit non-zero if no store returned a price (for scheduling)
  -v/--verbose         verbose logging
```

## Adding or fixing a store

Append an entry to `config/stores.yaml`. `defaults` are inherited unless overridden.

```yaml
  - id: technopolis
    name: "Technopolis"
    url: "https://www.technopolis.bg/<z-flip7-256gb-product-page>"
    method: jsonld          # css | jsonld | regex | custom
    # For method: css
    # selector: "[itemprop=price], .product-price-current"
    # price_regex: "([0-9][0-9\\s.,]*)"
    currency: EUR
    fetch: auto             # auto | http | browser
    search_query: "Samsung Galaxy Z Flip7 256GB Technopolis цена"
```

- **`method: jsonld`** is preferred where a store emits `schema.org` Product /
  Offer / AggregateOffer data — it survives layout redesigns. It reads
  `offers.price` (or `AggregateOffer.lowPrice`) and the offer's `priceCurrency`
  wins over the `currency` hint.
- **`method: css`** uses `selector` (a `content`/`data-price` attribute is
  preferred over text) with an optional `price_regex` cleanup.
- **`method: regex`** runs `price_regex` against the raw HTML.
- **`method: custom`** calls a named function in `tracker/adapters/custom.py`
  registered in its `PARSERS` dict — the escape hatch for tricky sites.

If a store first comes back `unavailable`, open its page in a browser, check
whether the price is in a JSON-LD block (use `jsonld`) or find a stable CSS
selector, and update the entry.

## Email (optional)

The manual run does not email. Set these env vars and pass `--email` to send a
report (HTML + plaintext). Missing vars → it silently skips.

```
SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASSWORD,
SMTP_FROM (default SMTP_USER), SMTP_TO, SMTP_TLS (default "1")
```

## Tests

```bash
pip install pytest
python -m pytest
```

Tests cover currency parsing/conversion, price extraction (JSON-LD / CSS / block
detection) against HTML fixtures, the diff engine (drops, new/lost listings,
changed-cheapest, first run), and snapshot persistence (skipped-day tolerance).
No network access is required.

## Networking note

The tracker makes outbound HTTPS requests to store websites. It must run in an
environment whose network policy **allows** access to those retail domains
(e.g. `emag.bg`, `pazaruvaj.com`). In a locked-down sandbox that blocks them,
every store will report `unavailable` — run it where egress to the stores is
open, or adjust the environment's network policy.

Even where egress is open, an individual store can still refuse a scrape:
some sites (typically Cloudflare-fronted aggregators such as `pazaruvaj.com`)
return an HTTP 403 anti-bot challenge and are reported `blocked` **with the
reason**, while direct retailers such as `emag.bg` serve their product JSON-LD
and return a live price. That is expected — the run continues and reports
whatever stores it could reach.

## Roadmap

- Add the remaining stores (Technopolis, Technomarket, Zora, Plesio, JAR,
  Ozone.bg, Samsung.bg, carriers, amazon.de) as `stores.yaml` entries.
- Schedule a daily run (cron / CI / a scheduled task) invoking `python -m tracker`
  and emailing the summary.
