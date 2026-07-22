"""Last-resort web-search fallback.

When both the HTTP and browser tiers fail for a store, this tier can try to
discover/verify a price via a web search. Running as a standalone script we
have no built-in search credentials, so this is a pluggable, best-effort hook:
it is a no-op unless a search provider is configured (SEARCH_PROVIDER env +
matching credentials). It never raises.

A result found here is tagged source="search" so the report never silently
trusts a lower-confidence number as if it were scraped.
"""

from __future__ import annotations

import os

from .adapters.base import ExtractResult
from .models import StoreConfig


def is_configured() -> bool:
    return bool(os.environ.get("SEARCH_PROVIDER"))


def search_price(cfg: StoreConfig) -> ExtractResult:
    """Attempt to find a price via search. No-op unless a provider is configured."""
    if not cfg.search_query:
        return ExtractResult(None, None, None, reason="no search_query configured")
    if not is_configured():
        return ExtractResult(
            None, None, None, reason="search fallback not configured (set SEARCH_PROVIDER)"
        )
    # Placeholder for a real provider integration (e.g. SerpAPI, Brave Search).
    # Intentionally not implemented to avoid shipping a fake price source.
    return ExtractResult(None, None, None, reason="search provider not implemented")
