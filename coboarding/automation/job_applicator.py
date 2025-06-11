import os
import json
import asyncio
import random
import logging
import base64
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Any
import argparse
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError, ElementHandle

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('job_application.log')
    ]
)
logger = logging.getLogger(__name__)

from ..ai.llm_client import LLMClient

class JobApplicator:
    def __init__(self, headless: bool = False, slow_mo: int = 100):
        self.headless = headless
        self.slow_mo = slow_mo  # Add delay between actions
        self.profile = self._load_profile()
        self.llm_client = LLMClient()
        self.timeout = 60000  # 60 seconds timeout
        
    def _load_profile(self) -> Dict:
        """Load user profile from JSON file"""
        profile_path = Path("data/profile.json")
        if not profile_path.exists():
            raise FileNotFoundError("Profile not found. Please create data/profile.json")
            
        with open(profile_path, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    async def fill_form(self, page: Page) -> bool:
        """Fill out the job application form with improved error handling"""
        try:
            logger.info("Starting form filling process")
            
            # Wait for the form to be interactive
            await self._wait_for_page_ready(page)
            
            # Take a screenshot of the initial form state
            await page.screenshot(path='form_initial.png')
            
            # Handle file uploads first, as some forms require files before enabling other fields
            logger.info("Checking for file upload fields...")
            await self._handle_file_uploads(page)
            
            # Wait a moment in case file uploads affect the form
            await asyncio.sleep(2)
            
            # Take another screenshot after file uploads
            await page.screenshot(path='after_uploads.png')
            
            # Common input field selectors - expanded with more variations
            field_selectors = [
                # First name fields
                ('input[name*="first" i], input[id*="first" i], input[placeholder*="first" i], '
                 'input[data-qa*="first" i], input[data-test*="first" i], input[class*="first" i]', 'first_name'),
                
                # Last name fields
                ('input[name*="last" i], input[id*="last" i], input[placeholder*="last" i], input[placeholder*="name" i], '
                 'input[data-qa*="last" i], input[data-test*="last" i], input[class*="last" i], input[class*="name" i]', 'last_name'),
                
                # Email fields
                ('input[type="email" i], input[name*="email" i], input[id*="email" i], input[placeholder*="email" i], '
                 'input[data-qa*="email" i], input[data-test*="email" i], input[class*="email" i]', 'email'),
                
                # Phone fields
                ('input[type="tel" i], input[name*="phone" i], input[name*="mobile" i], input[id*="phone" i], input[id*="mobile" i], '
                 'input[placeholder*="phone" i], input[placeholder*="mobile" i], input[placeholder*="tel" i], '
                 'input[data-qa*="phone" i], input[data-test*="phone" i], input[class*="phone" i], input[class*="mobile" i]', 'phone'),
                
                # Address fields
                ('input[name*="street" i], input[id*="street" i], input[name*="address" i], input[id*="address" i], '
                 'input[placeholder*="street" i], input[placeholder*="address" i], input[data-qa*="address" i], '
                 'input[data-test*="address" i], input[class*="address" i], input[class*="street" i]', 'address'),
            ]
            
            # Try multiple selector variations for each field
            for selectors, field in field_selectors:
                value = self._get_field_value(field)
                if value:
                    logger.info(f"Attempting to fill {field} field")
                    success = await self._try_selectors(page, selectors, value)
                    if not success:
                        logger.warning(f"Could not fill {field} field with any selector")
                    await asyncio.sleep(0.5)  # Small delay between fields
            
            # Handle file uploads
            await self._handle_file_uploads(page)
            
            # Try to submit the form
            return await self._submit_form(page)
            
        except Exception as e:
            logger.error(f"Error filling form: {str(e)}", exc_info=True)
            await page.screenshot(path='error_screenshot.png')
            return False
    
    def _get_field_value(self, field_name: str) -> str:
        """Get field value from profile with error handling"""
        try:
            if field_name == 'address':
                return self.profile['personal_info'].get('address', '').split(',')[0]
            return self.profile['personal_info'].get(field_name, '')
        except Exception as e:
            logger.warning(f"Could not get value for {field_name}: {str(e)}")
            return ''
            
    def _get_file_to_upload(self, file_type: str) -> Path:
        """Get the appropriate file to upload based on type"""
        file_mapping = {
            'resume': ['resume.pdf', 'cv.pdf', 'lebenslauf.pdf'],
            'cover_letter': ['cover_letter.pdf', 'anschreiben.pdf', 'motivation.pdf'],
            'certificates': ['certificates.pdf', 'zeugnisse.pdf'],
            'photo': ['photo.jpg', 'bild.jpg', 'profile.jpg']
        }
        
        # Look for files in the data directory
        data_dir = Path('data')
        
        for file_name in file_mapping.get(file_type, []):
            file_path = data_dir / file_name
            if file_path.exists():
                return file_path
                
        # If no specific file found, return the first one that exists
        for file_type in file_mapping:
            for file_name in file_mapping[file_type]:
                file_path = data_dir / file_name
                if file_path.exists():
                    return file_path
                    
        raise FileNotFoundError("No suitable file found for upload")

    async def _try_selectors(self, page: Page, selectors: str, value: str):
        """Try multiple selector variations to find and fill a field"""
        for selector in selectors.split(','):
            selector = selector.strip()
            try:
                if await self._is_element_visible(page, selector):
                    await self._fill_field_safely(page, selector, value)
                    return True
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {str(e)}")
        return False

    async def _is_element_visible(self, page: Page, selector: str) -> bool:
        """Check if element is visible and interactable"""
        try:
            await page.wait_for_selector(selector, state='visible', timeout=5000)
            return True
        except PlaywrightTimeoutError:
            return False

    async def _fill_field_safely(self, page: Page, selector: str, value: str):
        """Safely fill a form field with retries and human-like behavior"""
        try:
            logger.info(f"Filling field {selector} with value: {value}")
            
            # Click the field first to focus
            await page.click(selector, timeout=10000)
            
            # Clear existing value if any
            await page.evaluate(f"document.querySelector('{selector}').value = ''")
            
            # Type with random delays to simulate human typing
            for char in str(value):
                await page.type(selector, char, delay=random.uniform(50, 150))
                await asyncio.sleep(random.uniform(0.05, 0.15))
            
            # Blur the field to trigger any validation
            await page.evaluate(f"document.querySelector('{selector}').blur()")
            
            await asyncio.sleep(random.uniform(0.2, 0.5))
            return True
            
        except Exception as e:
            logger.warning(f"Could not fill {selector}: {str(e)}")
            return False
    
    async def _wait_for_page_ready(self, page: Page, timeout: int = 30000):
        """Wait for the page to be fully loaded and interactive"""
        try:
            await page.wait_for_load_state('networkidle', timeout=timeout)
            await page.wait_for_load_state('domcontentloaded', timeout=timeout)
            await page.wait_for_load_state('load', timeout=timeout)
            
            # Wait for common loading indicators to disappear
            loading_selectors = [
                '.loading', '.spinner', '.loader',
                'div[role="progressbar"]',
                '//*[contains(@class, "loading")]',
                '//*[contains(@class, "spinner")]'
            ]
            
            for selector in loading_selectors:
                try:
                    await page.wait_for_selector(selector, state='hidden', timeout=5000)
                except:
                    pass
                    
        except Exception as e:
            logger.warning(f"Page ready check warning: {str(e)}")

    async def _analyze_screenshot_with_llava(self, screenshot_path: str) -> List[Dict[str, Any]]:
        """Analyze screenshot with LLaVA to find potential upload elements"""
        try:
            # Check if the screenshot file exists
            if not os.path.exists(screenshot_path):
                logger.warning(f"Screenshot file not found: {screenshot_path}")
                return []
                
            try:
                from ..ai.llava_client import LLaVAClient
            except ImportError:
                logger.warning("LLaVA client not available. Install it with: pip install -e .[llava]")
                return []
            
            try:
                llava = LLaVAClient()
                logger.info("Analyzing page with LLaVA for upload elements...")
                
                prompt = """
                Analyze this screenshot of a web form and identify any file upload buttons or areas. 
                Look for elements like:
                - File input fields (type="file")
                - Buttons with text like 'Upload', 'Choose File', 'Browse', 'Hochladen', 'Datei auswählen'
                - Drag and drop areas
                - Icons that might indicate file upload functionality
                
                For each potential upload element you find, provide:
                1. A description of the element
                2. Its approximate position on the page (top-left, center, etc.)
                3. Any visible text or labels near it
                4. Your confidence level (high/medium/low)
                
                Respond with a JSON array of objects, each with these properties:
                - description: string
                - position: string
                - text_nearby: string
                - confidence: 'high'|'medium'|'low'
                - x: number (optional)
                - y: number (optional)
                """
                
                result = await llava.analyze_image(screenshot_path, prompt)
                return self._parse_llava_response(result.get('response', ''))
                
            except Exception as e:
                logger.warning(f"LLaVA analysis error: {str(e)}")
                return []
                
        except Exception as e:
            logger.warning(f"Error in LLaVA analysis: {str(e)}")
            return []
            
    def _parse_llava_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLaVA response to extract upload element information"""
        elements = []
        try:
            # This is a simplified parser - you might need to adjust based on your LLaVA response format
            sections = response.split('\n\n')
            for section in sections:
                if any(keyword in section.lower() for keyword in ['upload', 'browse', 'choose file', 'datei', 'hochladen']):
                    elements.append({
                        'description': section.strip(),
                        'confidence': self._extract_confidence(section)
                    })
        except Exception as e:
            logger.warning(f"Error parsing LLaVA response: {str(e)}")
        return elements
        
    def _extract_confidence(self, text: str) -> str:
        """Extract confidence level from text"""
        text = text.lower()
        if 'high' in text:
            return 'high'
        elif 'medium' in text:
            return 'medium'
        return 'low'
            
    async def _handle_file_uploads(self, page: Page) -> None:
        """Handle file uploads in the application form with improved detection"""
        try:
            # Take a full page screenshot for visual analysis
            screenshot_path = 'upload_analysis.png'
            await page.screenshot(path=screenshot_path, full_page=True)
            
            # Try visual analysis with LLaVA first
            visual_elements = await self._analyze_screenshot_with_llava(screenshot_path)
            
            # Standard file input selectors - expanded with more variations
            file_input_selectors = [
                'input[type="file"]',  # Standard file input
                '.file-upload',          # Common class for file upload areas
                '.upload-container',     # Another common class
                '.file-input',           # Another common class
                '[class*="upload"]',    # Any element with 'upload' in class
                'div[role="button"]',   # Sometimes file uploads are styled as buttons
                'button:has-text("Choose File")',
                'button:has-text("Datei auswählen")',  # German
                'button:has-text("Hochladen")',        # German for 'Upload'
                'button:has-text("Upload")',
                'button:has-text("Browse")',
                'button:has-text("Durchsuchen")',      # German for 'Browse'
                'label:has-text("CV"), label:has-text("Resume"), label:has-text("Lebenslauf")',
                'div[role="button"]:has-text("Upload")',
                '[data-test*="upload"], [data-test*="file"]',
                'a:has-text("Upload"), a:has-text("Browse")',
                'span:has-text("Upload"), span:has-text("Browse")',
                '*:is(button, div, span, a):has(> svg[aria-label*="upload" i])',
                '*:is(button, div, span, a):has(> i[class*="upload" i])',
                'input[accept*="pdf"], input[accept*="doc"]',  # Inputs that accept document files
                '[id*="file"], [name*="file"], [class*="file"]',  # Generic file-related attributes
                '[id*="cv"], [name*="cv"], [class*="cv"]',  # CV-specific selectors
                '[id*="resume"], [name*="resume"], [class*="resume"]',  # Resume-specific selectors
                '[id*="lebenslauf"], [name*="lebenslauf"]'  # German for resume
            ]
            
            # Look for file input fields in all frames with visual analysis integration
            file_inputs = []
            
            # Function to check elements in a frame
            async def check_elements_in_frame(frame, selector_list):
                frame_inputs = []
                for selector in selector_list:
                    try:
                        elements = await frame.query_selector_all(selector)
                        for element in elements:
                            try:
                                # Get element properties safely
                                tag_name = (await element.get_property('tagName')).lower()
                                input_type = await element.get_attribute('type') or ''
                                
                                # Check if it's a file input
                                if tag_name == 'input' and input_type.lower() == 'file':
                                    frame_inputs.append((frame, element, 'file_input', 1.0))
                                # Check if it's a clickable upload element
                                elif await self._is_clickable_upload_element(element):
                                    frame_inputs.append((frame, element, 'clickable', 0.8))
                            except Exception as e:
                                logger.debug(f"Error checking element: {str(e)}")
                                continue
                    except Exception as e:
                        logger.debug(f"Error with selector {selector}: {str(e)}")
                        continue
                return frame_inputs
            
            # Check in main frame
            try:
                main_frame_inputs = await check_elements_in_frame(page, file_input_selectors)
                file_inputs.extend(main_frame_inputs)
                logger.info(f"Found {len(main_frame_inputs)} file inputs in main frame")
            except Exception as e:
                logger.warning(f"Error checking main frame: {str(e)}")
            
            # Check in all iframes with better error handling
            frames = page.frames[1:]  # Skip the main frame (index 0)
            logger.info(f"Checking {len(frames)} iframes for file inputs")
            
            for i, frame in enumerate(frames, 1):
                try:
                    if frame != page.main_frame:  # Skip main frame again to be safe
                        logger.debug(f"Checking frame {i}/{len(frames)}")
                        frame_inputs = await check_elements_in_frame(frame, file_input_selectors)
                        if frame_inputs:
                            logger.info(f"Found {len(frame_inputs)} file inputs in frame {i}")
                            file_inputs.extend(frame_inputs)
                except Exception as e:
                    logger.debug(f"Error checking frame {i}: {str(e)}")
                    continue
                    
            # Also check for file inputs using a more direct approach
            try:
                direct_inputs = await page.query_selector_all('input[type="file"]')
                for input_elem in direct_inputs:
                    try:
                        if await input_elem.is_visible() and await input_elem.is_enabled():
                            file_inputs.append((page, input_elem, 'file_input', 1.0))
                    except Exception as e:
                        logger.debug(f"Error checking direct file input: {str(e)}")
                        continue
                if direct_inputs:
                    logger.info(f"Found {len(direct_inputs)} direct file inputs")
            except Exception as e:
                logger.debug(f"Error with direct file input detection: {str(e)}")
                    
            # Add visual elements from LLaVA analysis
            for element in visual_elements:
                if element['confidence'] == 'high':
                    # For visual elements, we'll try to click on the described area
                    file_inputs.append((page, None, 'visual', 0.9, element))
            
            # Sort elements by confidence (highest first)
            file_inputs.sort(key=lambda x: x[3], reverse=True)
            
            # Remove duplicates while preserving order and priority
            seen = set()
            unique_file_inputs = []
            
            for item in file_inputs:
                if len(item) == 5:  # Visual element
                    frame, elem, elem_type, confidence, visual_data = item
                    unique_id = f"visual_{hash(str(visual_data))}"
                else:  # Regular element
                    frame, elem, elem_type, confidence = item
                    try:
                        # Use a combination of frame URL and element properties for uniqueness
                        frame_url = frame.url if hasattr(frame, 'url') else 'main'
                        elem_id = await elem.evaluate('''el => {
                            return [
                                el.tagName,
                                el.id,
                                el.className,
                                el.getAttribute('type'),
                                el.getAttribute('role'),
                                el.getAttribute('aria-label')
                            ].join('|');
                        }''')
                        unique_id = f"{frame_url}:{elem_id}"
                    except Exception as e:
                        logger.debug(f"Error generating unique ID for element: {str(e)}")
                        continue
                
                if unique_id not in seen:
                    seen.add(unique_id)
                    unique_file_inputs.append(item)
            
            if not file_inputs:
                logger.info("No file upload fields found")
                return
                
            logger.info(f"Found {len(file_inputs)} file upload field(s)")
            
            for item in file_inputs:
                if len(item) == 5:  # Visual element from LLaVA
                    frame, input_field, field_type, confidence, visual_data = item
                    logger.info(f"Trying visual upload element: {visual_data['description']} (confidence: {confidence})")
                    
                    # Try to click on the described area
                    try:
                        # This is a simplified version - you might need to implement more sophisticated
                        # logic to convert visual description to coordinates
                        await page.mouse.click(visual_data.get('x', 100), visual_data.get('y', 100))
                        await asyncio.sleep(1)
                        
                        # Now try to handle the file chooser
                        try:
                            async with page.expect_file_chooser(timeout=5000) as fc_info:
                                await page.mouse.click(visual_data.get('x', 100), visual_data.get('y', 100))
                            file_chooser = await fc_info.value
                            await file_chooser.set_files(str(self._get_file_to_upload('resume')))
                            logger.info("File uploaded successfully via visual analysis")
                            continue
                        except Exception as e:
                            logger.debug(f"File chooser not triggered by visual click: {str(e)}")
                    except Exception as e:
                        logger.debug(f"Error clicking visual element: {str(e)}")
                    
                    continue
                    
                # Regular element handling
                frame, input_field, field_type, confidence = item
                try:
                    # Get the label or nearby text to identify the field
                    # Ensure we're working with the correct frame
                    if frame != page.main_frame:
                        await frame.wait_for_load_state('domcontentloaded')
                    
                    # Take a screenshot of the element for debugging
                    try:
                        await input_field.screenshot(path=f'upload_element_{len(seen)}.png')
                    except:
                        pass  # Screenshot not critical
                    label = await input_field.evaluate('''input => {
                        // Try to find associated label
                        if (input.id) {
                            const label = document.querySelector(`label[for="${input.id}"]`);
                            if (label) return label.textContent.trim();
                        }
                        
                        // Check for aria-label
                        if (input.getAttribute('aria-label')) {
                            return input.getAttribute('aria-label').trim();
                        }
                        
                        // Check for placeholder
                        if (input.placeholder) {
                            return input.placeholder.trim();
                        }
                        
                        // Try to find nearby text
                        let el = input;
                        for (let i = 0; i < 5; i++) {  // Increased depth
                            el = el.parentElement;
                            if (!el) break;
                            if (el.textContent && el.textContent.trim()) {
                                return el.textContent.trim().split('\n')[0].trim();
                            }
                        }
                        
                        // Try to find a heading before the input
                        const all_elements = Array.from(document.querySelectorAll('*'));
                        const index = all_elements.indexOf(input);
                        for (let i = Math.max(0, index - 10); i < index; i++) {
                            const el = all_elements[i];
                            if (['H1', 'H2', 'H3', 'H4', 'H5', 'H6'].includes(el.tagName)) {
                                return el.textContent.trim();
                            }
                        }
                        
                        return input.name || 'file';
                    }''')
                    
                    logger.info(f"Found file upload field: {label}")
                    
                    # Determine the type of file to upload based on the field label
                    file_path = None
                    
                    # Check for different file types based on label text
                    label_lower = label.lower()
                    
                    if any(term in label_lower for term in ['lebenslauf', 'cv', 'resume', 'curriculum vitae', 'bewerbung', 'application']):
                        file_path = Path("data/resume.pdf")
                        file_type = "resume"
                    elif any(term in label_lower for term in ['anschreiben', 'cover letter', 'motivationsschreiben']):
                        file_path = Path("data/cover_letter.pdf")
                        file_type = "cover letter"
                    elif any(term in label_lower for term in ['zeugnis', 'certificate', 'zertifikat', 'diploma']):
                        file_path = Path("data/certificates.pdf")
                        file_type = "certificate"
                    elif any(term in label_lower for term in ['bild', 'photo', 'foto']):
                        file_path = Path("data/photo.jpg")
                        file_type = "photo"
                    else:
                        # Default to resume if we can't determine the type
                        file_path = Path("data/resume.pdf")
                        file_type = "default file"
                    
                    # Check if the file exists
                    if file_path and file_path.exists():
                        logger.info(f"Uploading {file_type}: {file_path}")
                        
                        # Try different methods to upload the file
                        try:
                            # Method 1: Direct file input (standard)
                            if await input_field.is_visible():
                                logger.info(f"Attempting to upload {file_type} using direct input")
                                try:
                                    # Ensure the element is in view
                                    await input_field.scroll_into_view_if_needed()
                                    await input_field.set_input_files(str(file_path))
                                    await asyncio.sleep(1)  # Wait for any upload to complete
                                    
                                    # Verify the upload was successful if possible
                                    try:
                                        value = await input_field.evaluate('el => el.value')
                                        if value and Path(value).name == file_path.name:
                                            logger.info(f"{file_type.capitalize()} uploaded successfully")
                                            continue  # Move to next file input if successful
                                    except:
                                        logger.info(f"{file_type.capitalize()} upload attempted (verification skipped)")
                                        continue
                                        
                                except Exception as e:
                                    logger.debug(f"Direct file input failed: {str(e)}")
                                    raise  # Let it be caught by the outer try/except
                        except Exception as e:
                            logger.debug(f"Standard file upload failed: {str(e)}")
                        
                        try:
                            # Method 2: Click and use file chooser
                            try:
                                logger.info(f"Attempting to upload {file_type} using file chooser")
                                # Ensure we're in the right frame context
                                if frame != page.main_frame:
                                    await frame.wait_for_load_state('domcontentloaded')
                                    
                                # Scroll to the element and click it
                                await input_field.scroll_into_view_if_needed()
                                
                                # Wait for file chooser to appear
                                async with page.expect_file_chooser(timeout=5000) as fc_info:
                                    await input_field.click(delay=100)
                                
                                # Handle the file chooser
                                file_chooser = await fc_info.value
                                await file_chooser.set_files(str(file_path))
                                await asyncio.sleep(2)  # Wait for upload to complete
                                
                                logger.info(f"{file_type.capitalize()} uploaded via file chooser")
                                continue  # Move to next file input if successful
                                
                            except Exception as e:
                                logger.debug(f"File chooser method failed: {str(e)}")
                                raise  # Let it be caught by the outer try/except
                        except Exception as e:
                            logger.debug(f"File chooser upload failed: {str(e)}")
                        
                        logger.warning(f"All upload methods failed for {file_type}")
                    else:
                        logger.warning(f"{file_type.capitalize()} file not found at {file_path}")
                    
                except Exception as e:
                    logger.warning(f"Error handling file upload field: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.warning(f"Error in file upload handling: {str(e)}")
    
    async def _is_clickable_upload_element(self, element) -> bool:
        """Check if an element is likely a clickable upload element"""
        try:
            # First check basic properties that don't require JS evaluation
            try:
                if not (await element.is_visible() and await element.is_enabled()):
                    return False
            except:
                return False
            
            try:
                # Get element properties safely using evaluate
                element_info = await element.evaluate('''el => ({
                    tagName: el.tagName ? el.tagName.toLowerCase() : '',
                    role: el.getAttribute('role') || '',
                    onclick: el.getAttribute('onclick') || '',
                    className: el.className || '',
                    id: el.id || '',
                    name: el.getAttribute('name') || '',
                    type: el.getAttribute('type') || '',
                    text: el.textContent ? el.textContent.trim().toLowerCase() : ''
                })''')
                
                # Common patterns for upload elements
                upload_keywords = ['upload', 'browse', 'choose', 'select', 'file', 'hochladen', 'auswählen']
                
                # Check element properties for upload indicators
                if not element_info:
                    return False
                    
                # Check tag and role
                if element_info.get('tagName') == 'input' and element_info.get('type') == 'file':
                    return True
                    
                # Check class names
                class_name = element_info.get('className', '').lower()
                if any(keyword in class_name for keyword in upload_keywords):
                    return True
                    
                # Check text content
                text = element_info.get('text', '')
                if any(keyword in text for keyword in upload_keywords):
                    return True
                    
                # Check role and other attributes
                if element_info.get('role') == 'button' and any(keyword in text for keyword in ['upload', 'browse', 'choose']):
                    return True
                
                # Check for common upload button texts
                try:
                    text = (await element.text_content() or '').lower()
                    upload_phrases = [
                        'upload', 'browse', 'choose file', 'select file',
                        'hochladen', 'datei auswählen', 'datei hochladen',
                        'anhang', 'anlage', 'dokument hochladen',
                        'anhang hochladen', 'datei auswaehlen'
                    ]
                    
                    if any(phrase in text for phrase in upload_phrases):
                        return True
                except:
                    pass
                
                # Check for common button text patterns
                try:
                    value_attr = await element.get_attribute('value') or ''
                    if any(phrase in value_attr.lower() for phrase in ['upload', 'browse', 'hochladen']):
                        return True
                except:
                    pass
                
                # Check for common button types
                try:
                    type_attr = await element.get_attribute('type') or ''
                    if type_attr.lower() == 'button' and ('upload' in class_attr.lower() or 'file' in class_attr.lower()):
                        return True
                except:
                    pass
                
                return False
                
            except Exception as e:
                logger.debug(f"Error getting element properties: {str(e)}")
                return False
            
        except Exception as e:
            logger.debug(f"Error in _is_clickable_upload_element: {str(e)}")
            return False

    async def _submit_form(self, page: Page) -> bool:
        """Attempt to submit the form with multiple strategies"""
        # Take a screenshot before attempting to submit
        await page.screenshot(path='before_submit.png')
        
        # First, check for any iframes that might contain the form
        frames = page.frames
        if len(frames) > 1:  # More than just the main frame
            logger.info(f"Found {len(frames)} frames, checking for forms in iframes")
            for frame in frames[1:]:  # Skip the main frame (index 0)
                try:
                    if await frame.is_visible('form', timeout=1000):
                        logger.info(f"Found form in frame: {frame.name or frame.url}")
                        # Try to submit the form in this frame
                        await frame.evaluate('''() => {
                            const form = document.querySelector('form');
                            if (form) form.submit();
                        }''')
                        await asyncio.sleep(3)
                        return True
                except:
                    continue
        
        # Try to find and submit the form directly
        try:
            forms = await page.query_selector_all('form')
            if forms:
                logger.info(f"Found {len(forms)} forms on the page")
                for i, form in enumerate(forms):
                    try:
                        # Check if form is visible and has input fields
                        is_visible = await form.is_visible()
                        has_inputs = await form.query_selector_all('input, textarea, select')
                        
                        if is_visible and len(has_inputs) > 0:
                            logger.info(f"Submitting form {i+1} directly")
                            await form.evaluate('form => form.submit()')
                            await asyncio.sleep(3)
                            return True
                    except Exception as e:
                        logger.debug(f"Error submitting form {i+1}: {str(e)}")
                        continue
        except Exception as e:
            logger.debug(f"Direct form submission failed: {str(e)}")
        
        # Try various submit button selectors - ordered by likelihood
        submit_selectors = [
            # Specific to bewerbung.jobs
            'button[data-cy="apply-now-button"]',
            'button[data-testid="apply-button"]',
            'button[data-qa="submit-application"]',
            'button[class*="apply-button"]',
            'button[class*="submit-application"]',
            'button[class*="btn-apply"]',
            'button[class*="btn-submit"]',
            
            # Common button texts for job applications (German)
            'button:has-text("Jetzt bewerben")',  # 'Apply now' in German
            'button:has-text("Bewerbung absenden")',  # 'Submit application' in German
            'button:has-text("Bewerben")',  # German for 'Apply'
            'button:has-text("Senden")',     # German for 'Send'
            'button:has-text("Absenden")',   # German for 'Submit'
            'button:has-text("Bewerbung einreichen")',  # 'Submit application'
            'button:has-text("Bewerbung senden")',  # 'Send application'
            
            # Common button texts (English)
            'button:has-text("Apply Now")',
            'button:has-text("Submit Application")',
            'button:has-text("Send Application")',
            'button:has-text("Apply for this job")',
            'button:has-text("Submit")',
            'button:has-text("Apply")',
            
            # Common selectors
            'button[type="submit"]',
            'input[type="submit"]',
            'button[type="button"]',
            
            # Class-based selectors
            'button[class*="submit"]',
            'button[class*="apply"]',
            'button[class*="btn-primary"]',
            'button[class*="btn-submit"]',
            'button[class*="btn-apply"]',
            'input[class*="submit"]',
            'input[class*="apply"]',
            
            # ID-based selectors
            '#submit',
            '#apply',
            '#submitBtn',
            '#applyBtn',
            '#submit-button',
            '#apply-button',
            
            # Data-attribute selectors
            'button[data-qa*="submit"]',
            'button[data-test*="submit"]',
            'button[data-qa*="apply"]',
            'button[data-test*="apply"]',
            
            # More generic selectors
            'button:has-text("Weiter")',  # 'Next' in German
            'button:has-text("Next")',
            'button:has-text("Continue")',
            'button:has-text("Fortfahren")',  # 'Continue' in German
        ]
        
        # Also try to find any button that might be a submit button
        all_buttons = await page.query_selector_all('button, input[type="button"], input[type="submit"]')
        for idx, button in enumerate(all_buttons):
            try:
                text_content = await button.text_content()
                if text_content and any(word in text_content.lower() for word in ['submit', 'apply', 'bewerben', 'senden']):
                    logger.info(f"Clicking potential submit button with text: {text_content}")
                    await button.click()
                    await asyncio.sleep(3)
                    return True
            except:
                continue
        
        # Try clicking all buttons that might be submit buttons
        for selector in submit_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    try:
                        is_visible = await element.is_visible()
                        is_enabled = await element.is_enabled()
                        if is_visible and is_enabled:
                            logger.info(f"Clicking submit button: {selector}")
                            await element.scroll_into_view_if_needed()
                            await element.click(delay=100)
                            await asyncio.sleep(3)
                            
                            # Check for success indicators or errors
                            try:
                                await page.wait_for_load_state('networkidle', timeout=10000)
                                await page.wait_for_selector('.success, .thank-you, [class*="success"], [class*="thank"], [class*="confirmation"], [class*="success-message"]', 
                                                        state='visible', timeout=10000)
                                logger.info("Form submitted successfully!")
                                return True
                            except Exception as e:
                                logger.info("Form submission attempted, but couldn't verify success")
                                return True
                    except Exception as e:
                        logger.debug(f"Could not click element {selector}: {str(e)}")
                        continue
            except Exception as e:
                logger.debug(f"Submit button {selector} not found: {str(e)}")
                continue
        
        # Try to find and click any button that might be a submit button by text content
        try:
            all_clickables = await page.query_selector_all('button, a, [role="button"], [onclick], [href*="javascript:"]')
            logger.info(f"Found {len(all_clickables)} clickable elements on the page")
            
            # Sort by visibility (visible elements first)
            visible_clickables = []
            for element in all_clickables:
                try:
                    is_visible = await element.is_visible()
                    if is_visible:
                        visible_clickables.append(element)
                except:
                    continue
            
            logger.info(f"Found {len(visible_clickables)} visible clickable elements")
            
            # Try clicking visible elements that might be submit buttons
            for element in visible_clickables[:20]:  # Limit to first 20 to avoid too many attempts
                try:
                    text = (await element.text_content() or '').strip().lower()
                    if any(word in text for word in ['bewerb', 'senden', 'absenden', 'submit', 'apply', 'weiter', 'continue']):
                        logger.info(f"Clicking element with text: {text}")
                        await element.scroll_into_view_if_needed()
                        await element.click(delay=100)
                        await asyncio.sleep(3)
                        return True
                except Exception as e:
                    logger.debug(f"Error clicking element: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.debug(f"Error finding clickable elements: {str(e)}")
            
        # As a last resort, try pressing Enter in the last form field
        try:
            # Find all form fields
            form_fields = await page.query_selector_all('input:not([type="hidden"]), textarea, select')
            if form_fields:
                last_input = form_fields[-1]  # Get the last visible form field
                logger.info("Pressing Enter in the last input field")
                await last_input.focus()
                await last_input.press('Enter')
                await asyncio.sleep(3)
                
                # Check if the page changed after pressing Enter
                current_url = page.url
                if 'thank' in current_url.lower() or 'confirmation' in current_url.lower():
                    logger.info("Form submitted successfully after pressing Enter")
                    return True
                    
        except Exception as e:
            logger.debug(f"Failed to press Enter: {str(e)}")
            
        # Final attempt: Try to submit any form with JavaScript
        try:
            result = await page.evaluate('''() => {
                const forms = document.querySelectorAll('form');
                if (forms.length > 0) {
                    forms[0].submit();
                    return true;
                }
                return false;
            }''')
            if result:
                logger.info("Form submitted via JavaScript")
                await asyncio.sleep(3)
                return True
        except Exception as e:
            logger.debug(f"JavaScript form submission failed: {str(e)}")
        
        # Take a screenshot of the failed state
        await page.screenshot(path='submit_failed.png')
        
        # Log all buttons for debugging
        buttons = await page.query_selector_all('button, input[type="button"], input[type="submit"], a[role="button"]')
        logger.info(f"Found {len(buttons)} potential buttons on the page")
        for idx, button in enumerate(buttons):
            try:
                text = await button.text_content() or ''
                button_type = await button.get_attribute('type') or ''
                button_id = await button.get_attribute('id') or ''
                button_class = await button.get_attribute('class') or ''
                logger.info(f"Button {idx}: text='{text.strip()}', type='{button_type}', id='{button_id}', class='{button_class}'")
            except:
                continue
                
        logger.warning("No submit button found or form submission failed")
        return False

    async def apply(self, url: str):
        """Start the job application process with enhanced error handling"""
        browser = None
        try:
            async with async_playwright() as p:
                # Configure browser with additional options
                browser = await p.chromium.launch(
                    headless=self.headless,
                    slow_mo=self.slow_mo,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-infobars',
                        '--window-size=1920,1080',
                        '--start-maximized'
                    ]
                )
                
                # Create a new context with custom settings
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    locale='de-DE',
                    timezone_id='Europe/Berlin',
                    permissions=['geolocation'],
                    color_scheme='light',
                    java_script_enabled=True,
                    has_touch=False,
                    is_mobile=False,
                    reduced_motion='reduce',
                    screen={'width': 1920, 'height': 1080}
                )
                
                # Add custom headers to look more like a regular browser
                await context.set_extra_http_headers({
                    'Accept-Language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
                })
                
                # Create a new page and set viewport
                page = await context.new_page()
                await page.set_viewport_size({"width": 1920, "height": 1080})
                
                # Navigate to the URL with retries
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        logger.info(f"Navigating to {url} (attempt {attempt + 1}/{max_retries})")
                        await page.goto(url, timeout=60000, wait_until='domcontentloaded')
                        break
                    except Exception as e:
                        if attempt == max_retries - 1:
                            raise
                        logger.warning(f"Navigation attempt {attempt + 1} failed: {str(e)}")
                        await asyncio.sleep(2)
                
                logger.info(f"Successfully loaded application page at {url}")
                
                # Take a screenshot for debugging
                await page.screenshot(path='application_page.png')
                
                # Fill the application form
                success = await self.fill_form(page)
                
                if success:
                    logger.info("Application submitted successfully!")
                    # Take a final screenshot
                    await page.screenshot(path='submission_success.png')
                else:
                    logger.warning("There were issues with the application.")
                    # Take a screenshot of the failed state
                    await page.screenshot(path='submission_failed.png')
                
                # Keep the browser open for debugging if not in headless mode
                if not self.headless:
                    logger.info("Running in interactive mode. Press Enter to close the browser...")
                    input()
                
                return success
                
        except Exception as e:
            logger.error(f"An error occurred during application: {str(e)}", exc_info=True)
            if browser:
                try:
                    await page.screenshot(path='error_screenshot.png')
                except:
                    pass
            return False
        finally:
            if browser:
                await browser.close()

def parse_args():
    parser = argparse.ArgumentParser(description='Automate job applications')
    parser.add_argument('--url', type=str, required=True, help='Job application URL')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--slow-mo', type=int, default=100, 
                      help='Slow down Playwright operations by specified milliseconds')
    parser.add_argument('--timeout', type=int, default=60000,
                      help='Global timeout in milliseconds for page operations')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    return parser.parse_args()

async def main():
    load_dotenv()
    args = parse_args()
    
    # Configure logging level
    log_level = logging.DEBUG if args.debug else logging.INFO
    logger.setLevel(log_level)
    
    # Create necessary directories
    os.makedirs('data', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    logger.info(f"Starting job application process for URL: {args.url}")
    logger.info(f"Headless mode: {'enabled' if args.headless else 'disabled'}")
    
    try:
        applicator = JobApplicator(
            headless=args.headless,
            slow_mo=args.slow_mo
        )
        
        # Set global timeout if specified
        if args.timeout:
            applicator.timeout = args.timeout
        
        success = await applicator.apply(args.url)
        return 0 if success else 1
        
    except Exception as e:
        logger.critical(f"Critical error in main: {str(e)}", exc_info=True)
        return 1

def cli():
    """CLI entry point that wraps the async main function"""
    try:
        return asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application cancelled by user")
        return 1
    except Exception as e:
        logger.critical(f"Unhandled exception: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(cli())
