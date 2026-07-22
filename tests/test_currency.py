from decimal import Decimal

import pytest

from tracker import currency


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1 765,00 лв.", Decimal("1765.00")),   # EU grouping, comma decimal
        ("1.234,56 лв", Decimal("1234.56")),    # EU grouping with dot thousands
        ("902,43 €", Decimal("902.43")),        # euro, comma decimal
        ("1,234.56", Decimal("1234.56")),       # US grouping, dot decimal
        ("989.90", Decimal("989.90")),          # plain
        ("2149", Decimal("2149")),              # integer
        ("от 750,00 €", Decimal("750.00")),     # leading words
    ],
)
def test_parse_price(text, expected):
    assert currency.parse_price(text) == expected


@pytest.mark.parametrize("text", ["", "n/a", "цена при поискване", None, "лв."])
def test_parse_price_garbage(text):
    assert currency.parse_price(text) is None


def test_detect_currency():
    assert currency.detect_currency("902,43 €") == "EUR"
    assert currency.detect_currency("1 765,00 лв.") == "BGN"
    assert currency.detect_currency("1099.00", default="BGN") == "BGN"


def test_to_eur():
    assert currency.to_eur(Decimal("100"), "EUR") == Decimal("100.00")
    # 1.95583 BGN = 1 EUR
    assert currency.to_eur(Decimal("1.95583"), "BGN") == Decimal("1.00")
    assert currency.to_eur(Decimal("1955.83"), "BGN") == Decimal("1000.00")


def test_to_eur_unknown():
    with pytest.raises(ValueError):
        currency.to_eur(Decimal("10"), "USD")


def test_normalize_roundtrip():
    eur, raw, cur = currency.normalize("1 765,00 лв.", currency_hint="BGN")
    assert cur == "BGN"
    assert raw == "1 765,00 лв."
    assert eur == Decimal("902.43")  # 1765 / 1.95583, rounded
