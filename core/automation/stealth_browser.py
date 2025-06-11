import asyncio
import random
import logging
from typing import Dict, List, Optional
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

logger = logging.getLogger(__name__)

class StealthBrowser:
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
    async def initialize(self, headless: bool = False):
        """Initialize stealth browser with anti-detection measures
        
        Args:
            headless: Whether to run browser in headless mode (default: False for debugging)
        """
        # Initialize Playwright
        playwright = await async_playwright()
        self.playwright = playwright
        
        # Configure browser launch options
        launch_options = {
            'headless': headless,
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--single-process',
                '--disable-gpu',
                '--disable-extensions',
                '--disable-software-rasterizer',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-web-security',
                '--disable-site-isolation-trials',
            ],
        }
        
        # Launch browser with anti-detection measures
        self.browser = await self.playwright.chromium.launch(**launch_options)
        
        # Create a new context with stealth settings
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US,en;q=0.9',
            timezone_id='America/New_York',
            permissions=['geolocation', 'notifications'],
            color_scheme='dark',
            has_touch=False,
            java_script_enabled=True,
            ignore_https_errors=True,
        )
        
        # Create a new page
        self.page = await self.context.new_page()
        
        # Add stealth evasions
        await self._add_stealth_evasions()
        
        # Set extra HTTP headers
        await self.page.set_extra_http_headers({
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Referer': 'https://www.google.com/',
        })
        
        logger.info("Stealth browser initialized successfully")
        return self.page
    
    async def navigate(self, url: str, wait_until: str = "load", timeout: int = 30000):
        """Navigate to a URL with stealth measures
        
        Args:
            url: The URL to navigate to
            wait_until: When to consider navigation as complete ('load', 'domcontentloaded', 'networkidle')
            timeout: Maximum navigation time in milliseconds
        """
        if not self.page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")
            
        try:
            # Add random delay before navigation
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
            # Navigate to the URL
            await self.page.goto(url, wait_until=wait_until, timeout=timeout)
            
            # Randomize viewport size
            width = random.randint(1200, 1920)
            height = random.randint(800, 1080)
            await self.page.set_viewport_size({"width": width, "height": height})
            
            # Random mouse movements
            await self._random_mouse_movements()
            
            return True
            
        except Exception as e:
            logger.error(f"Error navigating to {url}: {str(e)}")
            raise
    
    async def new_page(self) -> Page:
        """Create a new page with randomized characteristics"""
        if not self.browser:
            await self.initialize()
            
        context = await self.browser.new_context(
            viewport={'width': random.randint(1200, 1920), 'height': random.randint(800, 1080)},
            user_agent=await self._get_random_user_agent(),
            locale=random.choice(['en-US', 'pl-PL', 'de-DE']),
        )
        
        page = await context.new_page()
        
        # Add human-like delays and mouse movements
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)
        
        return page
    
    async def human_type(self, page: Page, selector: str, text: str, delay_range=(50, 150)):
        """Type text with human-like delays"""
        element = await page.wait_for_selector(selector)
        await element.click()
        
        for char in text:
            await element.type(char)
            await asyncio.sleep(random.uniform(delay_range[0]/1000, delay_range[1]/1000))
    
    async def human_click(self, page: Page, selector: str):
        """Click with human-like mouse movement"""
        element = await page.wait_for_selector(selector)
        box = await element.bounding_box()
        
        if box:
            # Random position within element
            x = box['x'] + random.uniform(0.1, 0.9) * box['width']
            y = box['y'] + random.uniform(0.1, 0.9) * box['height']
            
            # Move mouse in steps
            await page.mouse.move(x, y, steps=random.randint(5, 15))
            await asyncio.sleep(random.uniform(0.1, 0.3))
            await page.mouse.click(x, y)
    
    async def _get_random_user_agent(self) -> str:
        """Get a random modern user agent"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        return random.choice(user_agents)
    
    async def _add_stealth_evasions(self):
        """Add evasions to avoid bot detection"""
        # Add multiple stealth scripts to avoid detection
        stealth_scripts = [
            # WebDriver detection
            """
            // Override webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
                set: () => {},
                configurable: true
            });
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
                configurable: true
            });
            
            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
                configurable: true
            });
            
            // Mock platform
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32',
                configurable: true
            });
            
            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            Object.defineProperty(navigator, 'permissions', {
                value: {
                    ...originalQuery,
                    query: (parameters) => {
                        if (parameters.name === 'notifications') {
                            return Promise.resolve({ state: 'default' });
                        }
                        return originalQuery(parameters);
                    }
                },
                configurable: true
            });
            
            // Mock chrome object
            window.chrome = {
                runtime: {},
                // Add other chrome properties as needed
            };
            
            // Mock webkitPersistentStorage
            if (!window.webkitPersistentStorage) {
                Object.defineProperty(window, 'webkitPersistentStorage', {
                    value: {
                        requestQuota: () => {},
                        queryUsageAndQuota: () => {}
                    },
                    configurable: true
                });
            }
            
            // Mock permissions API
            const originalPermissions = window.navigator.permissions;
            Object.defineProperty(navigator, 'permissions', {
                value: {
                    ...originalPermissions,
                    query: (parameters) => {
                        if (parameters.name === 'notifications') {
                            return Promise.resolve({ state: 'default' });
                        }
                        return originalPermissions.query(parameters);
                    }
                },
                configurable: true
            });
            """
        ]
        
        # Apply all stealth scripts
        for script in stealth_scripts:
            await self.page.add_init_script(script)
    
    async def close(self):
        """Close the browser and cleanup resources"""
        try:
            if hasattr(self, 'context') and self.context:
                await self.context.close()
                self.context = None
            
            if hasattr(self, 'browser') and self.browser:
                await self.browser.close()
                self.browser = None
                
            if hasattr(self, 'playwright') and self.playwright:
                await self.playwright.stop()
                self.playwright = None
                
            self.page = None
            logger.info("Browser resources cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error while closing browser: {str(e)}")
            raise