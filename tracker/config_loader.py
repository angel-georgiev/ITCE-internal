"""Load and validate config/stores.yaml into StoreConfig objects."""

from __future__ import annotations

from pathlib import Path

import yaml

from .models import StoreConfig

_VALID_METHODS = {"css", "jsonld", "regex", "custom"}
_VALID_FETCH = {"auto", "http", "browser"}

# Fields that may be supplied under `defaults:` and inherited by every store.
_DEFAULTABLE = ("timeout", "user_agent", "accept_language", "currency", "fetch", "method")


def load_stores(config_path: str | Path) -> list[StoreConfig]:
    """Parse the YAML config into a list of StoreConfig.

    Raises ValueError on malformed config so problems surface early.
    """
    path = Path(config_path)
    if not path.exists():
        raise ValueError(f"config file not found: {path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    defaults = data.get("defaults", {}) or {}
    raw_stores = data.get("stores", []) or []
    if not raw_stores:
        raise ValueError(f"no stores defined in {path}")

    stores: list[StoreConfig] = []
    seen_ids: set[str] = set()
    for i, raw in enumerate(raw_stores):
        if "id" not in raw or "name" not in raw or "url" not in raw:
            raise ValueError(f"store #{i} is missing required id/name/url")

        merged = {k: defaults[k] for k in _DEFAULTABLE if k in defaults}
        merged.update(raw)

        method = merged.get("method", "css")
        if method not in _VALID_METHODS:
            raise ValueError(f"store {merged['id']}: invalid method {method!r}")
        fetch = merged.get("fetch", "auto")
        if fetch not in _VALID_FETCH:
            raise ValueError(f"store {merged['id']}: invalid fetch {fetch!r}")
        if merged["id"] in seen_ids:
            raise ValueError(f"duplicate store id: {merged['id']}")
        seen_ids.add(merged["id"])

        stores.append(
            StoreConfig(
                id=merged["id"],
                name=merged["name"],
                url=merged["url"],
                method=method,
                selector=merged.get("selector"),
                price_regex=merged.get("price_regex"),
                currency=merged.get("currency", "BGN"),
                force_currency=merged.get("force_currency", False),
                fetch=fetch,
                enabled=merged.get("enabled", True),
                is_aggregator=merged.get("is_aggregator", False),
                custom_parser=merged.get("custom_parser"),
                search_query=merged.get("search_query"),
                timeout=merged.get("timeout", 20),
                user_agent=merged.get("user_agent", StoreConfig.user_agent),
                accept_language=merged.get("accept_language", StoreConfig.accept_language),
            )
        )
    return stores
