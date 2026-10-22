"""Playwright Headless Chromium Lifecycle Manager for Dynamic JS Rendering."""
from __future__ import annotations

import asyncio
from typing import Optional

from playwright.async_api import Browser, Playwright, async_playwright


class PlaywrightBrowserManager:
    """Singleton-style async manager for Headless Chromium pages."""

    def __init__(self) -> None:
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._lock = asyncio.Lock()

    async def get_browser(self) -> Browser:
        async with self._lock:
            if self._browser is None or not self._browser.is_connected():
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                    ],
                )
            return self._browser

    async def render_page_html(self, url: str, wait_ms: int = 1800) -> tuple[str, str]:
        """Navigate headless browser to URL and return (final_url, rendered_html)."""
        browser = await self.get_browser()
        context = await browser.new_context(
            locale="pt-BR",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 820},
        )
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=18000)
            await page.wait_for_timeout(wait_ms)
            html = await page.content()
            final_url = page.url
            return final_url, html
        finally:
            await context.close()

    async def shutdown(self) -> None:
        async with self._lock:
            if self._browser is not None:
                await self._browser.close()
                self._browser = None
            if self._playwright is not None:
                await self._playwright.stop()
                self._playwright = None
