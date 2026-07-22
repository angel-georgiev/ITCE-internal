"""Headless-browser fetch tier (Playwright + pre-installed Chromium).

Used only as a fallback when plain HTTP is blocked or the price isn't in the
static HTML. Import and launch are both best-effort: if Playwright or the
browser is unavailable, the tier degrades to a no-op and the run continues
with whatever the other tiers produced.
"""

from __future__ import annotations

import os

from .fetcher import FetchResult
from .models import StoreConfig

# Path to the Chromium bundled in this environment (see repo README / env).
_CHROMIUM_PATH = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH", "/opt/pw-browsers/chromium")


class BrowserFetcher:
    """Lazily-launched, reused headless Chromium wrapper."""

    def __init__(self) -> None:
        self._playwright = None
        self._browser = None
        self._available: bool | None = None

    def _ensure_started(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            from playwright.sync_api import sync_playwright

            self._playwright = sync_playwright().start()
            launch_kwargs = {"headless": True, "args": ["--no-sandbox"]}
            # Prefer Playwright's own resolution (PLAYWRIGHT_BROWSERS_PATH); fall
            # back to an explicit executable path if that fails.
            try:
                self._browser = self._playwright.chromium.launch(**launch_kwargs)
            except Exception:
                if os.path.exists(_CHROMIUM_PATH):
                    self._browser = self._playwright.chromium.launch(
                        executable_path=_CHROMIUM_PATH, **launch_kwargs
                    )
                else:
                    raise
            self._available = True
        except Exception:
            self._available = False
            self.close()
        return self._available

    def fetch(self, cfg: StoreConfig, *, wait_selector: str | None = None) -> FetchResult:
        """Render the page in Chromium and return the resulting DOM HTML."""
        if not self._ensure_started():
            return FetchResult(ok=False, reason="browser tier unavailable")

        context = None
        try:
            context = self._browser.new_context(
                user_agent=cfg.user_agent,
                locale="bg-BG",
                extra_http_headers={"Accept-Language": cfg.accept_language},
            )
            page = context.new_page()
            page.goto(cfg.url, timeout=cfg.timeout * 1000, wait_until="domcontentloaded")
            # Give client-side rendering / soft challenges a chance to settle.
            try:
                page.wait_for_load_state("networkidle", timeout=cfg.timeout * 1000)
            except Exception:
                pass
            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=5000)
                except Exception:
                    pass
            html = page.content()
            return FetchResult(ok=True, html=html, status_code=200)
        except Exception as exc:
            detail = str(exc).splitlines()[0][:160] if str(exc) else type(exc).__name__
            return FetchResult(ok=False, reason=f"browser error: {detail}")
        finally:
            if context is not None:
                try:
                    context.close()
                except Exception:
                    pass

    def close(self) -> None:
        for attr in ("_browser", "_playwright"):
            obj = getattr(self, attr, None)
            if obj is not None:
                try:
                    obj.stop() if attr == "_playwright" else obj.close()
                except Exception:
                    pass
                setattr(self, attr, None)
