import base64
from typing import Dict, List, Tuple, Optional
from playwright.async_api import Page
from core.ai.llm_client import LLMClient
from core.ai.vision_processor import VisionProcessor
import logging

logger = logging.getLogger(__name__)

class FormDetector:
    def __init__(self):
        self.llm_client = LLMClient()
        self.vision_processor = VisionProcessor()
        
    async def analyze_page(self, page: Page, language: str = "en") -> Dict:
        """Comprehensive form analysis using multiple approaches"""
        
        # 1. DOM-based analysis
        dom_analysis = await self._analyze_dom(page)
        
        # 2. Visual analysis
        screenshot = await page.screenshot(full_page=True)
        visual_analysis = await self._analyze_visually(screenshot, language)
        
        # 3. Tab navigation analysis
        tab_analysis = await self._analyze_with_tab_navigation(page)
        
        # 4. Combine results using LLM
        combined_analysis = await self._combine_analyses(
            dom_analysis, visual_analysis, tab_analysis, language
        )
        
        return combined_analysis
    
    async def _analyze_dom(self, page: Page) -> Dict:
        """Extract form elements from DOM"""
        form_elements = await page.evaluate("""
            () => {
                const forms = Array.from(document.querySelectorAll('form'));
                const inputs = Array.from(document.querySelectorAll('input, textarea, select'));
                const labels = Array.from(document.querySelectorAll('label'));
                
                const elements = [];
                
                inputs.forEach((input, index) => {
                    const rect = input.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {  // Visible elements only
                        elements.push({
                            type: input.type || input.tagName.toLowerCase(),
                            name: input.name || '',
                            id: input.id || '',
                            placeholder: input.placeholder || '',
                            required: input.required || false,
                            value: input.value || '',
                            className: input.className || '',
                            position: {
                                x: Math.round(rect.left),
                                y: Math.round(rect.top),
                                width: Math.round(rect.width),
                                height: Math.round(rect.height)
                            },
                            selector: `${input.tagName.toLowerCase()}${input.id ? '#' + input.id : ''}${input.className ? '.' + input.className.split(' ').join('.') : ''}`,
                            nearby_text: ''
                        });
                    }
                });
                
                // Add nearby text for context
                elements.forEach(element => {
                    const el = document.querySelector(element.selector);
                    if (el) {
                        const nearbyLabels = document.querySelectorAll(`label[for="${element.id}"]`);
                        if (nearbyLabels.length > 0) {
                            element.nearby_text = nearbyLabels[0].textContent.trim();
                        } else {
                            // Look for nearby text
                            const parent = el.parentElement;
                            if (parent) {
                                element.nearby_text = parent.textContent.replace(el.textContent, '').trim().substring(0, 100);
                            }
                        }
                    }
                });
                
                return {
                    elements: elements,
                    forms_count: forms.length,
                    total_inputs: inputs.length
                };
            }
        """)
        
        return form_elements
    
    async def _analyze_visually(self, screenshot: bytes, language: str) -> Dict:
        """Use vision model to analyze form visually"""
        prompt_template = {
            "en": "Analyze this webpage screenshot and identify all form fields, their types, and purposes. Focus on job application forms.",
            "pl": "Przeanalizuj ten zrzut ekranu strony internetowej i zidentyfikuj wszystkie pola formularza, ich typy i cele. Skup się na formularzach aplikacji o pracę.",
            "de": "Analysiere diesen Webseiten-Screenshot und identifiziere alle Formularfelder, ihre Typen und Zwecke. Konzentriere dich auf Bewerbungsformulare."
        }
        
        analysis = await self.vision_processor.analyze_image(
            screenshot, 
            prompt_template.get(language, prompt_template["en"])
        )
        
        return {"visual_analysis": analysis}
    
    async def _analyze_with_tab_navigation(self, page: Page) -> Dict:
        """Use tab navigation to discover focusable elements"""
        focusable_elements = []
        
        # Start from the beginning of the page
        await page.keyboard.press("Tab")
        
        for i in range(50):  # Max 50 tab presses to avoid infinite loops
            try:
                focused_element = await page.evaluate("""
                    () => {
                        const focused = document.activeElement;
                        if (focused && focused !== document.body) {
                            const rect = focused.getBoundingClientRect();
                            return {
                                tagName: focused.tagName.toLowerCase(),
                                type: focused.type || '',
                                name: focused.name || '',
                                id: focused.id || '',
                                placeholder: focused.placeholder || '',
                                className: focused.className || '',
                                position: {
                                    x: Math.round(rect.left),
                                    y: Math.round(rect.top),
                                    width: Math.round(rect.width),
                                    height: Math.round(rect.height)
                                },
                                text_content: focused.textContent ? focused.textContent.trim().substring(0, 50) : ''
                            };
                        }
                        return null;
                    }
                """)
                
                if focused_element and focused_element not in focusable_elements:
                    focusable_elements.append(focused_element)
                
                await page.keyboard.press("Tab")
                await page.wait_for_timeout(100)  # Small delay
                
            except Exception as e:
                logger.warning(f"Tab navigation error: {e}")
                break
        
        return {"focusable_elements": focusable_elements}
    
    async def _combine_analyses(self, dom_analysis: Dict, visual_analysis: Dict, 
                               tab_analysis: Dict, language: str) -> Dict:
        """Combine all analyses using LLM reasoning"""
        
        combined_prompt = f"""
        Analyze the following form detection data and provide a structured analysis:
        
        DOM Analysis: {dom_analysis}
        Visual Analysis: {visual_analysis}
        Tab Navigation: {tab_analysis}
        
        Please provide:
        1. Identified form fields with their purposes
        2. Required fields vs optional fields
        3. File upload fields (especially for CV/resume)
        4. Submit buttons and their selectors
        5. Any potential CAPTCHA or anti-bot measures
        6. Recommended filling order
        
        Format the response as JSON with clear field mappings.
        Language: {language}
        """
        
        analysis = await self.llm_client.generate(
            combined_prompt,
            model="mistral:7b",
            response_format="json"
        )
        
        return analysis