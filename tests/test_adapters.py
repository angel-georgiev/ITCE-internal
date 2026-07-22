from decimal import Decimal

from tracker.adapters.base import extract_price
from tracker.fetcher import build_headers, looks_blocked
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


def test_jsonld_tolerates_control_characters(html_fixture):
    # Real store JSON-LD often has literal newlines/tabs inside string values
    # (e.g. product descriptions). A strict json.loads() rejects them; the
    # extractor must tolerate them and still find the offer price.
    cfg = StoreConfig(id="emag", name="eMAG", url="x", method="jsonld", currency="EUR")
    ex = extract_price(html_fixture("emag_jsonld_control_chars.html"), cfg)
    assert ex.price_eur == Decimal("1098.08")
    assert ex.currency == "EUR"


def test_block_detection(html_fixture):
    assert looks_blocked(200, html_fixture("cloudflare_challenge.html")) is True
    assert looks_blocked(403, "") is True
    assert looks_blocked(200, "<html>real content 989,90 лв</html>") is False


def test_accept_encoding_only_advertises_decodable():
    # Advertising "br"/"zstd" without a decoder installed makes servers return
    # bytes requests can't inflate, silently breaking the fetch. The header must
    # list only encodings we can actually decode.
    import importlib.util

    cfg = StoreConfig(id="x", name="X", url="x")
    enc = build_headers(cfg)["Accept-Encoding"]
    advertised = {e.strip() for e in enc.split(",")}
    assert "gzip" in advertised and "deflate" in advertised
    if not (importlib.util.find_spec("brotli") or importlib.util.find_spec("brotlicffi")):
        assert "br" not in advertised
    if not importlib.util.find_spec("zstandard"):
        assert "zstd" not in advertised
