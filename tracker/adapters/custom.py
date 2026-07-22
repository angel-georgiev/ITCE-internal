"""Hand-written parsers for stores that need more than a selector/JSON-LD.

Register a parser by adding it to PARSERS with the key referenced from
stores.yaml (`custom_parser: <key>`). None are needed for the initial two
stores; this file is the escape hatch for later additions.

Each parser has the signature: parse(html: str, cfg: StoreConfig) -> ExtractResult
"""

from __future__ import annotations

from typing import Callable

# key -> callable
PARSERS: dict[str, Callable] = {}
