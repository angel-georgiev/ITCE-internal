"""Registry of named custom parsers referenced from stores.yaml (method: custom).

Kept separate from base.py to avoid an import cycle (custom parsers may want to
use helpers from base). Custom parsers have the signature:

    def parse(html: str, cfg: StoreConfig) -> ExtractResult
"""

from __future__ import annotations

from typing import Callable

# Populated lazily to sidestep import order between base <-> custom.
_REGISTRY: dict[str, Callable] | None = None


def _build() -> dict[str, Callable]:
    from . import custom

    return dict(custom.PARSERS)


def get_custom_parser(name: str | None):
    global _REGISTRY
    if not name:
        return None
    if _REGISTRY is None:
        _REGISTRY = _build()
    return _REGISTRY.get(name)
