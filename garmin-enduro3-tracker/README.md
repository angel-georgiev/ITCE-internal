# Garmin Enduro 3 Price Tracker (Bulgaria)

Automated daily price check for the Garmin Enduro 3 GPS smartwatch, across
four sources confirmed to ship to Bulgaria. Runs once a day at ~06:00
Bulgaria time via a Claude Code Remote **Routine** (a scheduled trigger that
spawns a fresh Claude session each day) — not a GitHub Actions workflow,
since the price lookup is agentic (`WebSearch`-driven) rather than a static
scraper. Direct HTTP scraping of these sites was tested and blocked by bot
protection (HTTP 403), so each run uses web search to find current listed
prices instead of fetching the pages directly.

## Sources tracked

| Source | What it is |
|---|---|
| [garmin.bg](https://garmin.bg/Enduro-3) | Official Garmin Bulgaria store |
| [pazaruvaj.com](https://www.pazaruvaj.com/p/garmin-enduro-3-010-02751-pP1120062670/) | Bulgarian price-comparison aggregator (covers emag.bg, technopolis.bg, ardes.bg, gps6.bg, etc.) |
| [amazon.de](https://www.amazon.de/dp/B0DHDCQZ8L) | Amazon Germany, ships EU-wide including Bulgaria |
| [bike24.com](https://www.bike24.com/p2866666.html) | German multisport retailer, ships EU-wide including Bulgaria |

## Data format

`price_history.json` is an array with one record per day. All prices are
normalized to **EUR** for direct comparison (BGN is currency-board pegged to
EUR at a fixed rate of 1 EUR = 1.95583 BGN); the native price/currency is
kept alongside for reference and buy-link accuracy.

```json
{
  "date": "2026-07-20",
  "sources": {
    "garmin.bg": {
      "price_eur": 868.85, "native_price": 1699, "native_currency": "BGN",
      "url": "https://garmin.bg/Enduro-3",
      "diff_vs_yesterday": 0.0, "diff_vs_alltime_low": 0.0
    },
    "pazaruvaj.com": {
      "price_eur": 636.55, "native_price": 1245, "native_currency": "BGN", "retailer": "gps6.bg",
      "url": "https://www.pazaruvaj.com/p/garmin-enduro-3-010-02751-pP1120062670/",
      "diff_vs_yesterday": -7.67, "diff_vs_alltime_low": 0.0
    },
    "amazon.de": {
      "price_eur": 679.00, "native_price": 679, "native_currency": "EUR",
      "url": "https://www.amazon.de/dp/B0DHDCQZ8L",
      "diff_vs_yesterday": 10.0, "diff_vs_alltime_low": 5.0
    },
    "bike24.com": {
      "price_eur": 699.00, "native_price": 699, "native_currency": "EUR",
      "url": "https://www.bike24.com/p2866666.html",
      "diff_vs_yesterday": 0.0, "diff_vs_alltime_low": 0.0
    }
  },
  "lowest": {"source": "pazaruvaj.com", "price_eur": 636.55}
}
```

If a source's price can't be determined on a given day, that source's entry
is recorded as `null` rather than failing the whole run.

## Notifications

Each run ends with a push notification (no email), e.g.:

```
Enduro3 lowest: €636.55 @pazaruvaj (-7.67). garmin.bg €868.85(=) | amazon.de €679(+10) | bike24 €699(=)
```

Full detail (buy links, native prices, diff vs. all-time low) lives in
`price_history.json`.

## Schedule caveat

The Routine's cron is fixed at 03:00 UTC (≈ 06:00 Bulgaria time during
EEST/summer). Bulgaria observes DST, so during EET/winter this lands at
~05:00 local time. Adjust the trigger's cron seasonally if exact 06:00 local
time matters.
