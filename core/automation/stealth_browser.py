import asyncio
import random
from typing import Dict, List, Optional
from botright import Botright
from playwright.async_api import Page, Browser
import logging

logger = logging.getLogger(__name__)

class StealthBrowser:
    def __init__(self):
        self.botright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
    async def initialize(self):
        """Initialize stealth browser with anti-detection measures"""
        self.botright = await Botright(
            headless=False,  # Set to True for production
            # Rotating user agents and fingerprints
            captcha_provider="capsolver",  # Free AI captcha solving
            stealth=True,
            block_webrtc=True,
            disable_blink_features=True,
        )
        self.browser = await self.botright.new_browser()
        
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
    
    async def close(self):
        """Clean shutdown"""
        if self.browser:
            await self.browser.close()
        if self.botright:
            await self.botright.close()