import base64
import asyncio
import httpx
from typing import Dict, List, Optional, Union
from PIL import Image
import io
import logging
from core.config import settings

logger = logging.getLogger(__name__)


class VisionProcessor:
    """Vision processing using LLaVA for form analysis and CV processing"""

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.vision_model = settings.CV_PARSER_MODEL  # LLaVA model
        self.timeout = 600  # 10 minutes for vision processing

    async def analyze_image(self, image_data: bytes, prompt: str, model: Optional[str] = None) -> str:
        """Analyze image using LLaVA vision model"""

        model = model or self.vision_model

        # Convert image to base64
        image_b64 = base64.b64encode(image_data).decode('utf-8')

        payload = {
            "model": model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 2048,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                response.raise_for_status()

                result = response.json()
                return result.get("response", "")

        except httpx.TimeoutException:
            logger.error(f"Timeout analyzing image with model {model}")
            raise Exception(f"Vision analysis timeout")
        except Exception as e:
            logger.error(f"Vision analysis error: {e}")
            raise

    async def analyze_form_screenshot(self, screenshot: bytes, language: str = "en") -> Dict:
        """Analyze form screenshot to identify form fields visually"""

        prompts = {
            "en": """
Analyze this webpage screenshot and identify all form elements. Focus on:

1. Input fields (text, email, phone, password, etc.)
2. File upload buttons
3. Dropdown menus and select boxes
4. Checkboxes and radio buttons
5. Text areas
6. Submit buttons
7. CAPTCHA elements
8. Required field indicators (*, red text, etc.)

For each form element, describe:
- Type of field
- Label or placeholder text
- Position on the page (top, middle, bottom, left, right)
- Whether it appears required
- Any special formatting or validation hints

Format your response as a structured analysis listing all identified form elements.
""",
            "pl": """
Przeanalizuj ten zrzut ekranu strony internetowej i zidentyfikuj wszystkie elementy formularza. Skup się na:

1. Polach wejściowych (tekst, email, telefon, hasło, itp.)
2. Przyciskach wgrywania plików
3. Menu rozwijanych
4. Polach wyboru i przyciskach opcji
5. Obszarach tekstowych
6. Przyciskach wysyłania
7. Elementach CAPTCHA
8. Wskaźnikach pól wymaganych (*, czerwony tekst, itp.)

Dla każdego elementu formularza opisz:
- Typ pola
- Tekst etykiety lub zastępczy
- Pozycję na stronie
- Czy wydaje się wymagane
- Wskazówki formatowania lub walidacji
""",
            "de": """
Analysiere diesen Webseiten-Screenshot und identifiziere alle Formularelemente. Konzentriere dich auf:

1. Eingabefelder (Text, E-Mail, Telefon, Passwort, etc.)
2. Datei-Upload-Buttons
3. Dropdown-Menüs und Auswahlboxen
4. Checkboxen und Radiobuttons
5. Textbereiche
6. Submit-Buttons
7. CAPTCHA-Elemente
8. Pflichtfeld-Indikatoren (*, roter Text, etc.)

Beschreibe für jedes Formularelement:
- Feldtyp
- Label- oder Platzhaltertext
- Position auf der Seite
- Ob es erforderlich erscheint
- Formatierungs- oder Validierungshinweise
"""
        }

        prompt = prompts.get(language, prompts["en"])

        analysis_text = await self.analyze_image(screenshot, prompt)

        # Convert text analysis to structured format
        return {
            "visual_analysis": analysis_text,
            "detected_elements": await self._extract_elements_from_analysis(analysis_text, language)
        }

    async def analyze_cv_image(self, cv_image: bytes, language: str = "en") -> str:
        """Extract text content from CV image using OCR"""

        prompts = {
            "en": """
Extract all text content from this CV/resume image. Pay special attention to:

1. Personal information (name, contact details)
2. Professional summary or objective
3. Work experience with dates and descriptions
4. Education details
5. Skills and competencies
6. Certifications and achievements
7. Any additional sections

Maintain the original structure and formatting as much as possible. 
Extract the text accurately, preserving dates, company names, and other important details.
""",
            "pl": """
Wyciągnij całą treść tekstową z tego obrazu CV. Zwróć szczególną uwagę na:

1. Informacje osobiste (imię, dane kontaktowe)
2. Podsumowanie zawodowe lub cel
3. Doświadczenie zawodowe z datami i opisami
4. Szczegóły wykształcenia
5. Umiejętności i kompetencje
6. Certyfikaty i osiągnięcia
7. Dodatkowe sekcje

Zachowaj oryginalną strukturę i formatowanie w miarę możliwości.
""",
            "de": """
Extrahiere den gesamten Textinhalt aus diesem Lebenslauf-Bild. Achte besonders auf:

1. Persönliche Informationen (Name, Kontaktdaten)
2. Berufliche Zusammenfassung oder Ziel
3. Berufserfahrung mit Daten und Beschreibungen
4. Bildungsdetails
5. Fähigkeiten und Kompetenzen
6. Zertifikate und Erfolge
7. Zusätzliche Abschnitte

Behalte die ursprüngliche Struktur und Formatierung bei.
"""
        }

        prompt = prompts.get(language, prompts["en"])
        return await self.analyze_image(cv_image, prompt)

    async def detect_form_fields(self, screenshot: bytes, language: str = "en") -> List[Dict]:
        """Detect specific form fields with coordinates and types"""

        prompts = {
            "en": """
Analyze this form screenshot and provide a detailed list of all form fields. For each field, provide:

1. Field type (text, email, phone, password, file, select, checkbox, radio, textarea, button)
2. Label text or placeholder
3. Approximate position (describe location on page)
4. Whether it appears required (look for *, red indicators, "required" text)
5. Any validation hints or formatting requirements
6. Field purpose (name, email, phone, address, etc.)

Format as a structured list with all identified fields.
""",
            "pl": """
Przeanalizuj ten zrzut ekranu formularza i podaj szczegółową listę wszystkich pól formularza. Dla każdego pola podaj:

1. Typ pola
2. Tekst etykiety lub zastępczy
3. Przybliżoną pozycję
4. Czy wydaje się wymagane
5. Wskazówki walidacji
6. Cel pola

Sformatuj jako strukturalną listę ze wszystkimi zidentyfikowanymi polami.
""",
            "de": """
Analysiere diesen Formular-Screenshot und gib eine detaillierte Liste aller Formularfelder an. Für jedes Feld gib an:

1. Feldtyp
2. Label-Text oder Platzhalter
3. Ungefähre Position
4. Ob es erforderlich erscheint
5. Validierungshinweise
6. Feldzweck

Formatiere als strukturierte Liste mit allen identifizierten Feldern.
"""
        }

        prompt = prompts.get(language, prompts["en"])
        analysis = await self.analyze_image(screenshot, prompt)

        # Parse the analysis into structured field data
        return await self._parse_field_analysis(analysis, language)

    async def compare_before_after(self, before_image: bytes, after_image: bytes, language: str = "en") -> Dict:
        """Compare form before and after filling to verify success"""

        # Analyze both images
        before_analysis = await self.analyze_image(
            before_image,
            "Describe all visible form fields and their current state (empty, filled, selected, etc.)"
        )

        after_analysis = await self.analyze_image(
            after_image,
            "Describe all visible form fields and their current state (empty, filled, selected, etc.)"
        )

        # Compare the states
        comparison_prompt = f"""
Compare these two form states and identify what changed:

BEFORE: {before_analysis}

AFTER: {after_analysis}

Provide analysis of:
1. Which fields were filled
2. Which fields remained empty
3. Any errors or validation messages
4. Whether the form appears successfully completed
5. Any unexpected changes or issues

Format as a structured comparison report.
"""

        comparison = await self.analyze_image(after_image, comparison_prompt)

        return {
            "before_state": before_analysis,
            "after_state": after_analysis,
            "comparison": comparison,
            "success_indicators": await self._extract_success_indicators(comparison)
        }

    async def _extract_elements_from_analysis(self, analysis_text: str, language: str) -> List[Dict]:
        """Extract structured elements from visual analysis text"""

        # This is a simplified implementation
        # In production, you might want to use more sophisticated NLP
        elements = []

        # Look for common form field indicators in the analysis
        field_keywords = {
            "en": ["input", "field", "textbox", "dropdown", "button", "checkbox", "upload", "file"],
            "pl": ["pole", "input", "przycisk", "menu", "upload", "plik", "checkbox"],
            "de": ["feld", "eingabe", "button", "dropdown", "upload", "datei", "checkbox"]
        }

        keywords = field_keywords.get(language, field_keywords["en"])

        lines = analysis_text.split('\n')
        for i, line in enumerate(lines):
            line_lower = line.lower()
            for keyword in keywords:
                if keyword in line_lower:
                    elements.append({
                        "line_number": i,
                        "description": line.strip(),
                        "type": "unknown",
                        "confidence": 0.5
                    })
                    break

        return elements

    async def _parse_field_analysis(self, analysis: str, language: str) -> List[Dict]:
        """Parse field analysis into structured data"""

        fields = []
        lines = analysis.split('\n')

        current_field = {}
        for line in lines:
            line = line.strip()
            if not line:
                if current_field:
                    fields.append(current_field)
                    current_field = {}
                continue

            # Simple parsing - can be enhanced with better NLP
            if any(keyword in line.lower() for keyword in ['field', 'input', 'button']):
                if current_field:
                    fields.append(current_field)
                current_field = {
                    "description": line,
                    "type": "unknown",
                    "label": "",
                    "required": False,
                    "position": "unknown"
                }
            elif current_field:
                # Add additional details to current field
                if 'required' in line.lower() or '*' in line:
                    current_field["required"] = True
                if 'label' in line.lower():
                    current_field["label"] = line

        if current_field:
            fields.append(current_field)

        return fields

    async def _extract_success_indicators(self, comparison: str) -> Dict:
        """Extract success indicators from comparison analysis"""

        success_keywords = ['success', 'completed', 'filled', 'submitted', 'confirmation']
        error_keywords = ['error', 'failed', 'invalid', 'required', 'missing']

        comparison_lower = comparison.lower()

        success_count = sum(1 for keyword in success_keywords if keyword in comparison_lower)
        error_count = sum(1 for keyword in error_keywords if keyword in comparison_lower)

        return {
            "likely_success": success_count > error_count,
            "success_indicators": success_count,
            "error_indicators": error_count,
            "confidence": min(1.0, abs(success_count - error_count) / max(1, success_count + error_count))
        }

    async def preprocess_image(self, image_data: bytes, enhance: bool = True) -> bytes:
        """Preprocess image for better OCR/analysis results"""

        try:
            # Open image with PIL
            image = Image.open(io.BytesIO(image_data))

            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')

            if enhance:
                from PIL import ImageEnhance, ImageFilter

                # Enhance contrast
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(1.2)

                # Enhance sharpness
                enhancer = ImageEnhance.Sharpness(image)
                image = enhancer.enhance(1.1)

                # Apply slight blur to reduce noise
                image = image.filter(ImageFilter.GaussianBlur(radius=0.5))

            # Convert back to bytes
            output = io.BytesIO()
            image.save(output, format='PNG', quality=95)
            return output.getvalue()

        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}")
            return image_data  # Return original if preprocessing fails

    async def health_check(self) -> bool:
        """Check if vision model is available"""
        try:
            # Test with a small dummy image
            test_image = Image.new('RGB', (100, 100), color='white')
            output = io.BytesIO()
            test_image.save(output, format='PNG')
            test_data = output.getvalue()

            # Try a simple analysis
            result = await self.analyze_image(test_data, "What do you see in this image?")
            return len(result) > 0

        except Exception as e:
            logger.error(f"Vision processor health check failed: {e}")
            return False