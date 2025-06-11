import os
import json
import asyncio
from pathlib import Path
from typing import Dict, Optional
import argparse
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page

from ..ai.llm_client import LLMClient

class JobApplicator:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.profile = self._load_profile()
        self.llm_client = LLMClient()
        
    def _load_profile(self) -> Dict:
        """Load user profile from JSON file"""
        profile_path = Path("data/profile.json")
        if not profile_path.exists():
            raise FileNotFoundError("Profile not found. Please create data/profile.json")
            
        with open(profile_path, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    async def fill_form(self, page: Page):
        """Fill out the job application form"""
        try:
            # Wait for the form to load
            await page.wait_for_selector('form', timeout=10000)
            
            # Fill personal information
            await self._fill_field(page, 'input[name="firstname"]', self.profile['personal_info']['first_name'])
            await self._fill_field(page, 'input[name="lastname"]', self.profile['personal_info']['last_name'])
            await self._fill_field(page, 'input[type="email"]', self.profile['personal_info']['email'])
            await self._fill_field(page, 'input[type="tel"]', self.profile['personal_info']['phone'])
            
            # Fill address
            await self._fill_field(page, 'input[name*="street"]', self.profile['personal_info']['address'].split(',')[0])
            
            # Handle file uploads
            resume_path = Path("data/resume.pdf")
            if resume_path.exists():
                await page.set_input_files('input[type="file"]', str(resume_path))
            
            # Submit the form
            await page.click('button[type="submit"]')
            
            return True
            
        except Exception as e:
            print(f"Error filling form: {str(e)}")
            return False
    
    async def _fill_field(self, page: Page, selector: str, value: str):
        """Helper method to fill a form field"""
        try:
            await page.fill(selector, value)
            await asyncio.sleep(0.5)  # Small delay between fields
        except Exception as e:
            print(f"Could not fill {selector}: {str(e)}")
    
    async def apply(self, url: str):
        """Start the job application process"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            
            try:
                page = await context.new_page()
                await page.goto(url, timeout=60000)
                
                print(f"Applying for position at {url}")
                
                # Fill the application form
                success = await self.fill_form(page)
                
                if success:
                    print("Application submitted successfully!")
                else:
                    print("There were issues with the application.")
                    
                # Keep the browser open for debugging if not in headless mode
                if not self.headless:
                    await page.pause()
                    
            except Exception as e:
                print(f"An error occurred: {str(e)}")
            finally:
                await browser.close()

def parse_args():
    parser = argparse.ArgumentParser(description='Automate job applications')
    parser.add_argument('--url', type=str, required=True, help='Job application URL')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    return parser.parse_args()

async def main():
    load_dotenv()
    args = parse_args()
    
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    applicator = JobApplicator(headless=args.headless)
    await applicator.apply(args.url)

if __name__ == "__main__":
    asyncio.run(main())
