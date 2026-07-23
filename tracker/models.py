"""Data models for the price tracker.

Kept dependency-free (stdlib only) so they can be imported by the pure logic
modules (currency, diff) without pulling in network libraries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

# Result status values.
STATUS_OK = "ok"
STATUS_UNAVAILABLE = "unavailable"  # page reached but no price found / out of stock
STATUS_BLOCKED = "blocked"  # bot protection / HTTP error
STATUS_ERROR = "error"  # unexpected exception during fetch or parse

# Where a price came from.
SOURCE_SCRAPE = "scrape"  # HTTP or browser DOM
SOURCE_SEARCH = "search"  # web-search fallback

# Which fetch tier produced the HTML.
TIER_HTTP = "http"
TIER_BROWSER = "browser"
TIER_SEARCH = "search"


@dataclass
class StoreConfig:
    """One store adapter, loaded from config/stores.yaml."""

    id: str
    name: str
    url: str
    method: str = "css"  # css | jsonld | regex | custom
    selector: str | None = None
    price_regex: str | None = None
    currency: str = "BGN"
    # Ignore any currency the page/JSON-LD declares and treat the raw amount as
    # `currency`. For stores whose markup mislabels the currency (e.g. TImobile
    # tags EUR prices as BGN), which would otherwise be converted incorrectly.
    force_currency: bool = False
    fetch: str = "auto"  # auto | http | browser
    enabled: bool = True
    is_aggregator: bool = False
    custom_parser: str | None = None
    search_query: str | None = None
    # Fetch behaviour (usually filled from `defaults` in the YAML).
    timeout: int = 20
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
    accept_language: str = "bg-BG,bg;q=0.9,en;q=0.8"


@dataclass
class PriceResult:
    """Outcome of fetching one store for one run."""

    store_id: str
    store_name: str
    status: str
    url: str
    source: str | None = None
    tier: str | None = None
    color: str | None = None
    price_eur: Decimal | None = None
    raw_price: str | None = None
    raw_currency: str | None = None
    is_aggregator: bool = False
    reason: str | None = None

    def to_dict(self) -> dict:
        return {
            "store_id": self.store_id,
            "store_name": self.store_name,
            "status": self.status,
            "source": self.source,
            "tier": self.tier,
            "url": self.url,
            "color": self.color,
            "price_eur": float(self.price_eur) if self.price_eur is not None else None,
            "raw_price": self.raw_price,
            "raw_currency": self.raw_currency,
            "is_aggregator": self.is_aggregator,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PriceResult":
        price = d.get("price_eur")
        return cls(
            store_id=d["store_id"],
            store_name=d["store_name"],
            status=d["status"],
            url=d.get("url", ""),
            source=d.get("source"),
            tier=d.get("tier"),
            color=d.get("color"),
            price_eur=Decimal(str(price)) if price is not None else None,
            raw_price=d.get("raw_price"),
            raw_currency=d.get("raw_currency"),
            is_aggregator=d.get("is_aggregator", False),
            reason=d.get("reason"),
        )


@dataclass
class Snapshot:
    """All results from a single run, persisted as one JSON file."""

    captured_at: str  # ISO-8601 UTC, also used as the filename stem
    results: list[PriceResult] = field(default_factory=list)
    schema_version: int = 1
    product: dict = field(
        default_factory=lambda: {
            "model": "Samsung Galaxy Z Flip 7",
            "storage": "256GB",
            "color": "cheapest per store",
        }
    )
    base_currency: str = "EUR"
    bgn_per_eur: float = 1.95583

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "captured_at": self.captured_at,
            "product": self.product,
            "base_currency": self.base_currency,
            "bgn_per_eur": self.bgn_per_eur,
            "results": [r.to_dict() for r in self.results],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Snapshot":
        return cls(
            captured_at=d["captured_at"],
            results=[PriceResult.from_dict(r) for r in d.get("results", [])],
            schema_version=d.get("schema_version", 1),
            product=d.get("product", {}),
            base_currency=d.get("base_currency", "EUR"),
            bgn_per_eur=d.get("bgn_per_eur", 1.95583),
        )

    def ok_results(self) -> list[PriceResult]:
        return [r for r in self.results if r.status == STATUS_OK and r.price_eur is not None]


@dataclass
class StoreDelta:
    """Change for one store between the previous run and the current run."""

    store_id: str
    store_name: str
    kind: str  # dropped | rose | unchanged | new_listing | lost_listing | new_store | removed_store
    current_eur: Decimal | None = None
    previous_eur: Decimal | None = None
    delta_eur: Decimal | None = None
    pct: Decimal | None = None
    is_aggregator: bool = False


@dataclass
class DiffReport:
    """Everything the reporters need about change since the previous run."""

    is_first_run: bool
    deltas: list[StoreDelta] = field(default_factory=list)
    cheapest: PriceResult | None = None
    previous_cheapest_store_id: str | None = None
    cheapest_changed: bool = False
    biggest_drop: StoreDelta | None = None
    biggest_pct_drop: StoreDelta | None = None
