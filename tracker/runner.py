"""Run all store adapters with per-store escalation and failure isolation.

Escalation for a store with fetch=auto:
  1. HTTP (requests)               -> extract
  2. headless browser (Playwright) -> extract   (if HTTP blocked or no price)
  3. web-search fallback           -> price      (only if --fallback / use_fallback)

A single store failing (blocked, timeout, selector miss, exception) never
aborts the run; it becomes a non-ok PriceResult and the loop continues.
"""

from __future__ import annotations

import logging

from . import fetcher, search_fallback
from .adapters.base import ExtractResult, extract_price
from .browser_fetcher import BrowserFetcher
from .models import (
    SOURCE_SCRAPE,
    SOURCE_SEARCH,
    STATUS_BLOCKED,
    STATUS_ERROR,
    STATUS_OK,
    STATUS_UNAVAILABLE,
    TIER_BROWSER,
    TIER_HTTP,
    TIER_SEARCH,
    PriceResult,
    StoreConfig,
)

log = logging.getLogger(__name__)


def _ok_result(cfg: StoreConfig, ex: ExtractResult, *, source: str, tier: str) -> PriceResult:
    return PriceResult(
        store_id=cfg.id,
        store_name=cfg.name,
        status=STATUS_OK,
        url=cfg.url,
        source=source,
        tier=tier,
        color=ex.color,
        price_eur=ex.price_eur,
        raw_price=ex.raw_price,
        raw_currency=ex.currency,
        is_aggregator=cfg.is_aggregator,
    )


def _fetch_and_extract(cfg: StoreConfig, browser: BrowserFetcher, use_fallback: bool) -> PriceResult:
    reason = "not attempted"
    blocked = False

    # Tier 1: HTTP
    if cfg.fetch in ("auto", "http"):
        fr = fetcher.fetch(cfg)
        if fr.ok and fr.html:
            ex = extract_price(fr.html, cfg)
            if ex.price_eur is not None:
                return _ok_result(cfg, ex, source=SOURCE_SCRAPE, tier=TIER_HTTP)
            reason = f"http: {ex.reason}"
        else:
            blocked = fr.blocked
            reason = f"http: {fr.reason}"

    # Tier 2: headless browser
    if cfg.fetch in ("auto", "browser"):
        log.info("browser tier for %s", cfg.id)
        br = browser.fetch(cfg, wait_selector=cfg.selector if cfg.method == "css" else None)
        if br.ok and br.html:
            ex = extract_price(br.html, cfg)
            if ex.price_eur is not None:
                return _ok_result(cfg, ex, source=SOURCE_SCRAPE, tier=TIER_BROWSER)
            reason = f"browser: {ex.reason}"
        else:
            reason = f"browser: {br.reason}"

    # Tier 3: web-search fallback
    if use_fallback:
        log.info("search fallback for %s", cfg.id)
        ex = search_fallback.search_price(cfg)
        if ex.price_eur is not None:
            return _ok_result(cfg, ex, source=SOURCE_SEARCH, tier=TIER_SEARCH)
        reason = f"{reason}; search: {ex.reason}"

    status = STATUS_BLOCKED if blocked else STATUS_UNAVAILABLE
    return PriceResult(
        store_id=cfg.id,
        store_name=cfg.name,
        status=status,
        url=cfg.url,
        is_aggregator=cfg.is_aggregator,
        reason=reason,
    )


def run(stores: list[StoreConfig], *, use_fallback: bool = False) -> list[PriceResult]:
    """Fetch every enabled store, returning one PriceResult each."""
    active = [s for s in stores if s.enabled]
    browser = BrowserFetcher()
    results: list[PriceResult] = []
    try:
        for cfg in active:
            try:
                results.append(_fetch_and_extract(cfg, browser, use_fallback))
            except Exception as exc:  # noqa: BLE001 - isolate any adapter failure
                log.exception("unexpected error for %s", cfg.id)
                results.append(
                    PriceResult(
                        store_id=cfg.id,
                        store_name=cfg.name,
                        status=STATUS_ERROR,
                        url=cfg.url,
                        is_aggregator=cfg.is_aggregator,
                        reason=f"error: {type(exc).__name__}: {exc}",
                    )
                )
    finally:
        browser.close()
    return results
