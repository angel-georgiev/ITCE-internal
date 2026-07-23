"""Headless-browser fetch tier (Playwright + pre-installed Chromium).

Used only as a fallback when plain HTTP is blocked or the price isn't in the
static HTML. Import and launch are both best-effort: if Playwright or the
browser is unavailable, the tier degrades to a no-op and the run continues
with whatever the other tiers produced.

Two environment realities this tier must cope with:

* **Outbound proxy.** Many sandboxes route all egress through an HTTP proxy
  (``HTTPS_PROXY``). Unlike ``requests``, Chromium does not pick that up from
  the environment on its own, so we detect it and pass it to Playwright. Without
  this the browser silently talks to nothing and every navigation resets.
* **``headless_shell`` vs full Chromium.** Playwright's default headless build
  (``chrome-headless-shell``) can return empty responses behind a
  TLS-re-terminating proxy where the full Chromium binary succeeds, so we launch
  the full binary by ``executable_path`` when we can find it.
"""

from __future__ import annotations

import logging
import os

from .fetcher import FetchResult
from .models import StoreConfig

log = logging.getLogger(__name__)

# Path to the full Chromium bundled in this environment (see repo README / env).
# Preferred over Playwright's default headless_shell build (see module docstring).
_CHROMIUM_PATH = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH", "/opt/pw-browsers/chromium")

# Proxy env vars, in priority order. HTTPS first: store pages are all https.
_PROXY_ENV_VARS = ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy")


def detect_proxy(environ: dict[str, str] | None = None) -> str | None:
    """Return the outbound proxy URL from the environment, or None.

    Chromium needs the proxy passed explicitly; it does not read these env vars
    the way requests/curl do.
    """
    env = environ if environ is not None else os.environ
    for var in _PROXY_ENV_VARS:
        val = env.get(var)
        if val:
            return val
    return None


def build_launch_kwargs(proxy: str | None) -> dict:
    """Assemble Playwright launch kwargs, wiring the proxy through when present."""
    kwargs: dict = {
        "headless": True,
        "args": ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
    }
    if proxy:
        kwargs["proxy"] = {"server": proxy}
    return kwargs


class BrowserFetcher:
    """Lazily-launched, reused headless Chromium wrapper."""

    def __init__(self) -> None:
        self._playwright = None
        self._browser = None
        self._available: bool | None = None

    def _launch(self):
        """Launch Chromium, preferring the full binary over headless_shell."""
        kwargs = build_launch_kwargs(detect_proxy())
        if kwargs.get("proxy"):
            log.info("browser tier routing through proxy %s", kwargs["proxy"]["server"])
        # Prefer the full Chromium binary at a known path; fall back to whatever
        # Playwright resolves on its own (PLAYWRIGHT_BROWSERS_PATH) if that fails.
        if os.path.exists(_CHROMIUM_PATH):
            try:
                return self._playwright.chromium.launch(
                    executable_path=_CHROMIUM_PATH, **kwargs
                )
            except Exception:
                log.warning("full Chromium launch failed; trying default", exc_info=True)
        return self._playwright.chromium.launch(**kwargs)

    def _ensure_started(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            from playwright.sync_api import sync_playwright

            self._playwright = sync_playwright().start()
            self._browser = self._launch()
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
