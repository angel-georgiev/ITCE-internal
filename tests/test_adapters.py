from decimal import Decimal

from tracker.adapters.base import extract_price
from tracker.fetcher import looks_blocked
from tracker.models import StoreConfig


def test_jsonld_offer_emag(html_fixture):
    cfg = StoreConfig(id="emag", name="eMAG", url="x", method="jsonld", currency="EUR")
    ex = extract_price(html_fixture("emag.html"), cfg)
    assert ex.price_eur == Decimal("989.90")
    assert ex.currency == "EUR"


def test_jsonld_aggregate_offer_pazaruvaj(html_fixture):
    cfg = StoreConfig(id="paz", name="pazaruvaj", url="x", method="jsonld", currency="EUR")
    ex = extract_price(html_fixture("pazaruvaj.html"), cfg)
    # lowPrice from the AggregateOffer
    assert ex.price_eur == Decimal("902.43")
    assert ex.currency == "EUR"


def test_jsonld_currency_overrides_config_hint(html_fixture):
    # Config says BGN, but the JSON-LD says EUR — JSON-LD must win.
    cfg = StoreConfig(id="emag", name="eMAG", url="x", method="jsonld", currency="BGN")
    ex = extract_price(html_fixture("emag.html"), cfg)
    assert ex.price_eur == Decimal("989.90")  # treated as EUR, not divided


def test_css_extraction_with_content_attr(html_fixture):
    cfg = StoreConfig(
        id="g", name="Generic", url="x", method="css",
        selector="span.price", currency="BGN",
    )
    ex = extract_price(html_fixture("generic_css.html"), cfg)
    # content="1099.00", currency BGN -> 1099 / 1.95583 = 561.91
    assert ex.price_eur == Decimal("561.91")


def test_css_missing_selector():
    cfg = StoreConfig(id="g", name="Generic", url="x", method="css", selector=".nope")
    ex = extract_price("<html><body>no price here</body></html>", cfg)
    assert ex.price_eur is None
    assert ex.reason


def test_block_detection(html_fixture):
    assert looks_blocked(200, html_fixture("cloudflare_challenge.html")) is True
    assert looks_blocked(403, "") is True
    assert looks_blocked(200, "<html>real content 989,90 лв</html>") is False
