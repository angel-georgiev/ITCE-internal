"""Price extraction from HTML.

Pure (no network): given HTML text + a StoreConfig, produce an ExtractResult.
The same extractor runs regardless of whether the HTML came from the HTTP tier
or the headless browser tier.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal

from bs4 import BeautifulSoup

from .. import currency as currency_mod
from ..models import StoreConfig
from .registry import get_custom_parser


@dataclass
class ExtractResult:
    price_eur: Decimal | None
    raw_price: str | None
    currency: str | None
    color: str | None = None
    reason: str | None = None


def _fail(reason: str) -> ExtractResult:
    return ExtractResult(price_eur=None, raw_price=None, currency=None, reason=reason)


def _from_raw(raw: str | None, cfg: StoreConfig, color: str | None = None) -> ExtractResult:
    if cfg.force_currency:
        # Ignore any currency marker in the text; treat the amount as cfg.currency.
        amount = currency_mod.parse_price(raw)
        if amount is None:
            return _fail("price not parseable")
        cur = cfg.currency.upper()
        try:
            price_eur = currency_mod.to_eur(amount, cur)
        except ValueError:
            return _fail(f"unsupported currency {cur!r}")
        return ExtractResult(
            price_eur=price_eur, raw_price=(raw.strip() if raw else None), currency=cur, color=color
        )
    price_eur, raw_price, cur = currency_mod.normalize(raw, currency_hint=cfg.currency)
    if price_eur is None:
        return _fail("price not parseable")
    return ExtractResult(price_eur=price_eur, raw_price=raw_price, currency=cur, color=color)


def _extract_css(soup: BeautifulSoup, cfg: StoreConfig) -> ExtractResult:
    if not cfg.selector:
        return _fail("no selector configured")
    node = soup.select_one(cfg.selector)
    if node is None:
        return _fail("selector matched nothing")
    # Prefer a content/price attribute when present (common on itemprop=price).
    raw = (
        node.get("content")
        or node.get("data-price")
        or node.get_text(" ", strip=True)
    )
    if cfg.price_regex and raw:
        m = re.search(cfg.price_regex, raw)
        if m:
            raw = m.group(1) if m.groups() else m.group(0)
    return _from_raw(raw, cfg)


def _iter_jsonld_objects(soup: BeautifulSoup):
    for script in soup.find_all("script", type="application/ld+json"):
        text = script.string or script.get_text()
        if not text:
            continue
        try:
            # strict=False tolerates literal control characters (newlines, tabs)
            # inside string values — common in real-world JSON-LD product
            # descriptions, which json.loads() rejects by default.
            data = json.loads(text, strict=False)
        except (json.JSONDecodeError, ValueError):
            continue
        stack = [data]
        while stack:
            item = stack.pop()
            if isinstance(item, dict):
                yield item
                stack.extend(item.values())
            elif isinstance(item, list):
                stack.extend(item)


def _offer_price(offer: dict) -> tuple[str | None, str | None]:
    """Pull (price, priceCurrency) from an Offer / AggregateOffer dict."""
    price = offer.get("price") or offer.get("lowPrice") or offer.get("lowprice")
    cur = offer.get("priceCurrency") or offer.get("pricecurrency")
    if price is None:
        spec = offer.get("priceSpecification")
        if isinstance(spec, dict):
            price = spec.get("price")
            cur = cur or spec.get("priceCurrency")
    return (str(price) if price is not None else None, cur)


def _extract_jsonld(soup: BeautifulSoup, cfg: StoreConfig) -> ExtractResult:
    candidates: list[tuple[Decimal, str, str]] = []  # (eur, raw, currency)
    for obj in _iter_jsonld_objects(soup):
        offers = obj.get("offers")
        if offers is None:
            continue
        offer_list = offers if isinstance(offers, list) else [offers]
        for offer in offer_list:
            if not isinstance(offer, dict):
                continue
            raw, cur = _offer_price(offer)
            if raw is None:
                continue
            amount = currency_mod.parse_price(raw)
            if amount is None:
                continue
            # A store's declared currency wins by default, but force_currency
            # overrides it for markup that mislabels the currency.
            cur = cfg.currency.upper() if cfg.force_currency else (cur or cfg.currency).upper()
            try:
                eur = currency_mod.to_eur(amount, cur)
            except ValueError:
                continue
            candidates.append((eur, raw, cur))
    if not candidates:
        return _fail("no JSON-LD offer price found")
    # Cheapest offer (e.g. cheapest color / seller).
    eur, raw, cur = min(candidates, key=lambda c: c[0])
    return ExtractResult(price_eur=eur, raw_price=raw, currency=cur)


def _extract_regex(html: str, cfg: StoreConfig) -> ExtractResult:
    if not cfg.price_regex:
        return _fail("no price_regex configured")
    m = re.search(cfg.price_regex, html)
    if not m:
        return _fail("regex matched nothing")
    raw = m.group(1) if m.groups() else m.group(0)
    return _from_raw(raw, cfg)


def extract_price(html: str, cfg: StoreConfig) -> ExtractResult:
    """Dispatch to the configured extraction method."""
    if not html:
        return _fail("empty html")

    if cfg.method == "custom":
        parser = get_custom_parser(cfg.custom_parser)
        if parser is None:
            return _fail(f"unknown custom parser {cfg.custom_parser!r}")
        return parser(html, cfg)

    if cfg.method == "regex":
        return _extract_regex(html, cfg)

    soup = BeautifulSoup(html, "lxml")
    if cfg.method == "jsonld":
        return _extract_jsonld(soup, cfg)
    return _extract_css(soup, cfg)
