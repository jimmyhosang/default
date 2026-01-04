"""
Browser automation tools using Playwright.
"""
from typing import Optional, Any
import logging
import asyncio

logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available. Browser automation disabled.")


class BrowserTools:
    """
    Browser automation for web interactions.
    Uses Playwright for reliable cross-browser automation.
    """
    
    def __init__(self, headless: bool = True, browser_type: str = "chromium"):
        """
        Initialize BrowserTools.
        
        Args:
            headless: Run browser without visible window.
            browser_type: Browser to use ("chromium", "firefox", "webkit").
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright is required for browser automation")
        
        self.headless = headless
        self.browser_type = browser_type
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None

    async def start(self) -> dict:
        """
        Start the browser.
        
        Returns:
            Dict with status.
        """
        self._playwright = await async_playwright().start()
        browser_launcher = getattr(self._playwright, self.browser_type)
        self._browser = await browser_launcher.launch(headless=self.headless)
        self._page = await self._browser.new_page()
        logger.info(f"Started {self.browser_type} browser (headless={self.headless})")
        return {"status": "success", "action": "start", "browser": self.browser_type}

    async def stop(self) -> dict:
        """
        Close the browser.
        
        Returns:
            Dict with status.
        """
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._browser = None
        self._page = None
        self._playwright = None
        logger.info("Browser stopped")
        return {"status": "success", "action": "stop"}

    async def navigate(self, url: str) -> dict:
        """
        Navigate to a URL.
        
        Args:
            url: URL to navigate to.
            
        Returns:
            Dict with status and page title.
        """
        if not self._page:
            await self.start()
        
        await self._page.goto(url)
        title = await self._page.title()
        logger.info(f"Navigated to: {url} - Title: {title}")
        return {"status": "success", "action": "navigate", "url": url, "title": title}

    async def click(self, selector: str) -> dict:
        """
        Click an element.
        
        Args:
            selector: CSS selector of the element.
            
        Returns:
            Dict with status.
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        
        await self._page.click(selector)
        logger.info(f"Clicked element: {selector}")
        return {"status": "success", "action": "click", "selector": selector}

    async def fill(self, selector: str, text: str) -> dict:
        """
        Fill an input field.
        
        Args:
            selector: CSS selector of the input.
            text: Text to fill.
            
        Returns:
            Dict with status.
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        
        await self._page.fill(selector, text)
        logger.info(f"Filled element {selector} with text")
        return {"status": "success", "action": "fill", "selector": selector}

    async def get_text(self, selector: str) -> dict:
        """
        Get text content of an element.
        
        Args:
            selector: CSS selector of the element.
            
        Returns:
            Dict with text content.
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        
        text = await self._page.text_content(selector)
        return {"status": "success", "selector": selector, "text": text}

    async def screenshot(self, path: Optional[str] = None, full_page: bool = False) -> dict:
        """
        Take a screenshot.
        
        Args:
            path: Optional path to save screenshot.
            full_page: Capture full scrollable page.
            
        Returns:
            Dict with screenshot data or path.
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        
        screenshot_bytes = await self._page.screenshot(path=path, full_page=full_page)
        logger.info(f"Screenshot taken (full_page={full_page})")
        
        result = {"status": "success", "action": "screenshot", "full_page": full_page}
        if path:
            result["path"] = path
        else:
            result["bytes_length"] = len(screenshot_bytes)
        return result

    async def evaluate(self, script: str) -> dict:
        """
        Execute JavaScript in page context.
        
        Args:
            script: JavaScript code to execute.
            
        Returns:
            Dict with result.
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        
        result = await self._page.evaluate(script)
        logger.info("Executed JavaScript in page")
        return {"status": "success", "action": "evaluate", "result": result}

    async def wait_for_selector(self, selector: str, timeout: int = 30000) -> dict:
        """
        Wait for an element to appear.
        
        Args:
            selector: CSS selector.
            timeout: Max wait time in milliseconds.
            
        Returns:
            Dict with status.
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        
        await self._page.wait_for_selector(selector, timeout=timeout)
        logger.info(f"Element appeared: {selector}")
        return {"status": "success", "action": "wait", "selector": selector}

    async def get_page_content(self) -> dict:
        """
        Get the full HTML content of the page.
        
        Returns:
            Dict with HTML content.
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        
        content = await self._page.content()
        return {"status": "success", "action": "get_content", "length": len(content), "content": content}
