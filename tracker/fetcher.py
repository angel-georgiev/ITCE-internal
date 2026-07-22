"""HTTP fetching with browser-like headers and bot-block detection.

This is the fast, first-choice tier. It deliberately stays thin so most of
its logic (block detection, header building) is unit-testable without a
network.
"""

from __future__ import annotations

import importlib.util
import time
from dataclasses import dataclass

import requests

from .models import StoreConfig


def _supported_accept_encoding() -> str:
    """Advertise only the content-encodings we can actually decode.

    requests decodes gzip/deflate out of the box, but brotli ("br") and zstd
    need optional packages. Advertising "br" without a decoder makes servers
    (e.g. Cloudflare-fronted eMAG) return brotli bytes that requests can't
    inflate, leaving resp.text as undecodable garbage — the fetch "succeeds"
    but no price is ever found. Only offer what's installed.
    """
    encodings = ["gzip", "deflate"]
    if importlib.util.find_spec("brotli") or importlib.util.find_spec("brotlicffi"):
        encodings.append("br")
    if importlib.util.find_spec("zstandard"):
        encodings.append("zstd")
    return ", ".join(encodings)


_ACCEPT_ENCODING = _supported_accept_encoding()

# Markers that indicate a bot-protection interstitial rather than real content.
_CHALLENGE_MARKERS = (
    "just a moment",
    "cf-chl",
    "cf_chl",
    "/cdn-cgi/challenge-platform",
    "attention required",
    "please enable javascript and cookies",
    "px-captcha",
    "distil_r_captcha",
)
_BLOCK_STATUSES = {401, 403, 405, 406, 429, 503}


@dataclass
class FetchResult:
    ok: bool
    html: str | None = None
    status_code: int | None = None
    blocked: bool = False
    reason: str | None = None


def build_headers(cfg: StoreConfig) -> dict[str, str]:
    return {
        "User-Agent": cfg.user_agent,
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": cfg.accept_language,
        "Accept-Encoding": _ACCEPT_ENCODING,
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


def looks_blocked(status_code: int, body: str) -> bool:
    """True if the response looks like a bot-protection block/challenge."""
    if status_code in _BLOCK_STATUSES:
        return True
    low = body.lower()
    return any(marker in low for marker in _CHALLENGE_MARKERS)


def fetch(cfg: StoreConfig, *, retries: int = 1, backoff: float = 2.0) -> FetchResult:
    """GET the store URL. Returns a FetchResult; never raises for network errors."""
    headers = build_headers(cfg)
    last_reason = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(
                cfg.url, headers=headers, timeout=cfg.timeout, allow_redirects=True
            )
            body = resp.text or ""
            if looks_blocked(resp.status_code, body):
                return FetchResult(
                    ok=False,
                    html=body,
                    status_code=resp.status_code,
                    blocked=True,
                    reason=f"blocked (HTTP {resp.status_code})",
                )
            if resp.status_code >= 400:
                last_reason = f"HTTP {resp.status_code}"
            else:
                return FetchResult(ok=True, html=body, status_code=resp.status_code)
        except requests.RequestException as exc:
            last_reason = f"request error: {type(exc).__name__}"
        if attempt < retries:
            time.sleep(backoff * (attempt + 1))
    return FetchResult(ok=False, reason=last_reason or "fetch failed")
