"""
Core automation module for browser interactions and form handling.
"""

from pathlib import Path
from typing import Optional, Union, Dict, List, Any
import asyncio
import logging
from .stealth_browser import StealthBrowser
from playwright.async_api import Page, Browser, BrowserContext

logger = logging.getLogger(__name__)

class BrowserAutomation(StealthBrowser):
    """
    Enhanced browser automation with form filling and content extraction capabilities.
    Extends StealthBrowser with additional functionality for testing and automation.
    """
    
    def __init__(self, headless: bool = False, slow_mo: int = 100):
        """
        Initialize the browser automation.
        
        Args:
            headless: Whether to run browser in headless mode
            slow_mo: Delay between actions in milliseconds for human-like behavior
        """
        super().__init__()
        self.headless = headless
        self.slow_mo = slow_mo
        self.timeout = 60000  # Default timeout in ms
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def initialize(self):
        """Initialize the browser with custom settings"""
        await super().initialize()
        self.browser = await self._init_browser()
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=await self._get_random_user_agent(),
            locale='en-US',
            permissions=['clipboard-read', 'clipboard-write']
        )
        self.page = await self.context.new_page()
    
    async def _init_browser(self) -> Browser:
        """Initialize the Playwright browser instance"""
        from playwright.async_api import async_playwright
        
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--window-size=1920,1080',
                '--start-maximized'
            ]
        )
        return browser
    
    async def navigate(self, url: str, timeout: Optional[int] = None):
        """Navigate to a URL with error handling"""
        if not self.page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")
        
        timeout = timeout or self.timeout
        try:
            await self.page.goto(url, timeout=timeout, wait_until='domcontentloaded')
            await self.page.wait_for_load_state('networkidle')
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to {url}: {str(e)}")
            return False
    
    async def extract_content(self, selector: str, timeout: Optional[int] = None) -> str:
        """Extract text content from a selector"""
        if not self.page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")
        
        timeout = timeout or self.timeout
        try:
            element = await self.page.wait_for_selector(selector, timeout=timeout)
            return await element.inner_text()
        except Exception as e:
            logger.error(f"Failed to extract content: {str(e)}")
            return ""
    
    async def capture_screenshot(self, output_path: Union[str, Path], full_page: bool = True) -> Path:
        """Capture a screenshot of the current page"""
        if not self.page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        await self.page.screenshot(path=str(output_path), full_page=full_page)
        return output_path
    
    async def close(self):
        """Close the browser and clean up resources"""
        if hasattr(self, 'context') and self.context:
            await self.context.close()
        if hasattr(self, 'browser') and self.browser:
            await self.browser.close()
        await super().close()


def validate_selector(selector: str) -> bool:
    """
    Validate a CSS selector.
    
    Args:
        selector: The CSS selector to validate
        
    Returns:
        bool: True if the selector is valid
        
    Raises:
        ValueError: If the selector is invalid
    """
    if not selector or not isinstance(selector, str):
        raise ValueError("Selector must be a non-empty string")
    
    # Basic validation - check for invalid characters
    import re
    
    # Regex pattern for valid CSS selectors
    # This is a simplified version that covers most common cases
    pattern = r'^[a-zA-Z0-9_\-\[\]="\'\s>+~#.:*^$|,()]+$'
    
    if not re.match(pattern, selector):
        raise ValueError(f"Invalid CSS selector: {selector}")
    
    # Check for common invalid patterns
    invalid_patterns = [
        '**', '//', '\\', '&&', '||', '!!', '[]', '()',
        '  ', '>>', '++', '~~', '..', '##', '::', ',,',
    ]
    
    for pattern in invalid_patterns:
        if pattern in selector:
            raise ValueError(f"Invalid pattern in selector: {pattern}")
    
    return True


__all__ = ['BrowserAutomation', 'validate_selector', 'StealthBrowser']