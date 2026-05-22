"""
DRAVION v.9 — Browser Automation (PHANTOM)

Playwright-based browser control:
  - Navigate to URLs and capture screenshots
  - Extract page text/content
  - Fill forms and click elements
  - Web scraping
"""
import asyncio
import os
import base64
import io
from datetime import datetime
from core.logger import log


class BrowserAgent:
    def __init__(self):
        self._browser = None
        self._page = None
        log.info("browser_agent_ready")

    async def _ensure_browser(self):
        if self._browser and self._page:
            return
        try:
            from playwright.async_api import async_playwright
            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch(headless=True)
            self._page = await self._browser.new_page()
        except Exception as e:
            raise RuntimeError(f"Browser init failed (run 'playwright install chromium'): {e}")

    async def navigate(self, url: str) -> str:
        """Navigate to URL, return page title."""
        await self._ensure_browser()
        try:
            await self._page.goto(url, wait_until="domcontentloaded", timeout=15000)
            title = await self._page.title()
            return f"Navigated to: {title} ({url})"
        except Exception as e:
            return f"Navigation failed: {e}"

    async def get_page_text(self, url: str = None) -> str:
        """Get text content of current or specified page."""
        await self._ensure_browser()
        if url:
            await self._page.goto(url, wait_until="domcontentloaded", timeout=15000)
        text = await self._page.inner_text("body")
        # Truncate for LLM context
        return text[:3000] if text else "No text content found."

    async def screenshot_url(self, url: str) -> str:
        """Screenshot a URL, save to Desktop, return path."""
        await self._ensure_browser()
        await self._page.goto(url, wait_until="networkidle", timeout=20000)
        ts = datetime.now().strftime("%H%M%S")
        path = os.path.join(os.path.expanduser("~"), "Desktop", f"web_{ts}.png")
        await self._page.screenshot(path=path, full_page=False)
        return f"Screenshot saved: {path}"

    async def extract_links(self, url: str = None) -> str:
        """Extract all links from current or specified page."""
        await self._ensure_browser()
        if url:
            await self._page.goto(url, wait_until="domcontentloaded", timeout=15000)
        links = await self._page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => ({text: e.innerText.trim().slice(0,60), href: e.href})).filter(l => l.text && l.href.startsWith('http')).slice(0, 20)"
        )
        if not links:
            return "No links found on this page."
        return "\n".join(f"- {l['text']}: {l['href']}" for l in links)

    async def fill_and_submit(self, url: str, selector: str, value: str) -> str:
        """Fill a form field and optionally submit."""
        await self._ensure_browser()
        if url:
            await self._page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await self._page.fill(selector, value)
        return f"Filled '{selector}' with value."

    async def click(self, selector: str) -> str:
        """Click an element on the current page."""
        await self._ensure_browser()
        await self._page.click(selector, timeout=5000)
        await self._page.wait_for_load_state("domcontentloaded")
        title = await self._page.title()
        return f"Clicked. Page now: {title}"

    async def close(self):
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._page = None


browser_agent = BrowserAgent()
