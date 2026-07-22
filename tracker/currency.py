"""Price-string parsing and currency normalization to EUR.

Pure: no network, no clock, no filesystem.
"""

from __future__ import annotations

import re
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

# Bulgaria's legally locked euro conversion rate (fixed, never fetched).
BGN_PER_EUR = Decimal("1.95583")

_TWOPLACES = Decimal("0.01")

# Currency hints found inside raw price strings.
_BGN_MARKERS = ("лв", "lv", "bgn", "лева")
_EUR_MARKERS = ("€", "eur")

# Strip everything that is not a digit or a separator, keeping the number.
_NUMBER_RE = re.compile(r"[0-9][0-9\s.,  ]*[0-9]|[0-9]")


def detect_currency(text: str, default: str = "BGN") -> str:
    """Guess the currency from markers inside a raw price string."""
    low = text.lower()
    if any(m in low for m in _EUR_MARKERS):
        return "EUR"
    if any(m in low for m in _BGN_MARKERS):
        return "BGN"
    return default


def parse_price(text: str | None) -> Decimal | None:
    """Extract a numeric amount from a messy price string.

    Handles both EU grouping ("1.234,56" / "1 234,56") and US/amazon.de
    grouping ("1,234.56") by treating the *last* separator as the decimal
    point. Returns None when no sensible number is present.
    """
    if not text:
        return None
    match = _NUMBER_RE.search(text)
    if not match:
        return None
    raw = match.group(0)
    # Normalize odd whitespace used as thousands separators.
    raw = raw.replace(" ", " ").replace(" ", " ").strip()

    last_dot = raw.rfind(".")
    last_comma = raw.rfind(",")

    if last_dot == -1 and last_comma == -1:
        cleaned = raw.replace(" ", "")
    elif last_comma > last_dot:
        # Comma is the decimal separator (EU style): drop dots/spaces, comma -> dot.
        cleaned = raw.replace(".", "").replace(" ", "").replace(",", ".")
    else:
        # Dot is the decimal separator (US style): drop commas/spaces.
        cleaned = raw.replace(",", "").replace(" ", "")

    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None
    if value <= 0:
        return None
    return value


def to_eur(amount: Decimal, currency: str) -> Decimal:
    """Convert an amount in the given currency to EUR, rounded to 2 dp."""
    cur = (currency or "").upper()
    if cur == "EUR":
        value = amount
    elif cur == "BGN":
        value = amount / BGN_PER_EUR
    else:
        raise ValueError(f"unsupported currency: {currency!r}")
    return value.quantize(_TWOPLACES, rounding=ROUND_HALF_UP)


def normalize(text: str | None, currency_hint: str = "BGN") -> tuple[Decimal | None, str | None, str]:
    """Parse a raw price string and normalize to EUR.

    Returns (price_eur, raw_price_str, detected_currency). price_eur is None
    when the string can't be parsed.
    """
    amount = parse_price(text)
    currency = detect_currency(text or "", default=currency_hint)
    if amount is None:
        return None, (text.strip() if text else None), currency
    return to_eur(amount, currency), (text.strip() if text else None), currency
