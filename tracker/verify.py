"""Independent price verification: is the scraped price the one being charged?

A store's scraped price (from JSON-LD / CSS) can silently disagree with the price
a human actually pays. The failure mode seen in practice: the markup carries the
pre-discount *regular* price while the page prominently displays a lower *sale*
price, so the tracker reports a number nobody is charged.

This module re-reads the page and warns only in that high-confidence case — a
struck-through regular price (`<del>`) that matches the scraped price, alongside a
lower sale price (`<ins>`). It is deliberately narrow: a false "verify" warning on
a correct row is worse than silence, so it never guesses at which element is "the"
price. When it can't find that exact sale pattern, it stays silent (ok).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from bs4 import BeautifulSoup, Tag

from . import currency as currency_mod

# A number immediately followed by a currency marker (EUR or BGN).
_PRICE_TOKEN = re.compile(r"\d[\d\s.,  ]*\d\s*(?:€|лв|lv|bgn|eur)", re.I)

# Leaf price paragraphs worth inspecting for a regular/sale split. Kept to the
# price node itself (not a wrapper like .summary) so a block's <del>/<ins> pair
# belongs to one product and can't be crossed with an accessory's sale price.
_PRICE_BLOCK_SELECTORS = "p.price, .price, .product-new-price"


@dataclass
class VerifyResult:
    ok: bool
    note: str | None = None


def _amounts_eur(text: str) -> list[Decimal]:
    """Every currency-tagged amount in `text`, normalized to EUR."""
    out: list[Decimal] = []
    for m in _PRICE_TOKEN.finditer(text or ""):
        tok = m.group(0)
        amount = currency_mod.parse_price(tok)
        if amount is None:
            continue
        try:
            out.append(currency_mod.to_eur(amount, currency_mod.detect_currency(tok, "EUR")))
        except ValueError:
            continue
    return out


def _amounts_in(nodes: list[Tag]) -> list[Decimal]:
    out: list[Decimal] = []
    for n in nodes:
        out.extend(_amounts_eur(n.get_text(" ", strip=True)))
    return out


def verify_price(
    html: str | None, price_eur: Decimal | None, *, tolerance: Decimal = Decimal("1")
) -> VerifyResult:
    """Warn when the scraped price looks like a regular price hiding a live sale.

    Returns ok=True (no warning) unless the page shows a struck-through regular
    price equal to the scraped price together with a lower sale price — in which
    case it reports the sale price the shopper actually pays.
    """
    if price_eur is None or not html:
        return VerifyResult(ok=True)
    soup = BeautifulSoup(html, "lxml")

    for block in soup.select(_PRICE_BLOCK_SELECTORS):
        regulars = _amounts_in(block.select("del"))
        sales = _amounts_in(block.select("ins"))
        if not regulars or not sales:
            continue
        # Anchor on the regular price matching what we scraped; the lower <ins>
        # is then the price actually charged. Anchoring this way keeps accessory
        # or unrelated regular/sale pairs (whose regular != our price) from firing.
        if any(abs(r - price_eur) <= tolerance for r in regulars):
            sale = min(sales)
            if sale < price_eur - tolerance:
                return VerifyResult(
                    ok=False,
                    note=f"page sale price €{sale:,.2f}, scraped regular €{price_eur:,.2f}",
                )
    return VerifyResult(ok=True)
