import asyncio
from typing import Dict, List, Optional, Union
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image
import io
from core.ai.llm_client import LLMClient
from core.ai.vision_processor import VisionProcessor
import spacy
import logging

logger = logging.getLogger(__name__)


class CVParser:
    def __init__(self):
        self.llm_client = LLMClient()
        self.vision_processor = VisionProcessor()
        self.nlp_models = {}
        self._load_spacy_models()

    def _load_spacy_models(self):
        """Load spaCy models for different languages"""
        model_mapping = {
            "en": "en_core_web_sm",
            "pl": "pl_core_news_sm",
            "de": "de_core_news_sm"
        }

        for lang, model_name in model_mapping.items():
            try:
                self.nlp_models[lang] = spacy.load(model_name)
            except OSError:
                logger.warning(f"spaCy model {model_name} not found for {lang}")
                self.nlp_models[lang] = None

    async def parse_cv(self, file_path: str, language: str = "en") -> Dict:
        """Parse CV from various formats (PDF, DOCX, image)"""
        file_path = Path(file_path)
        file_extension = file_path.suffix.lower()

        # Extract text based on file type
        if file_extension == '.pdf':
            text_content, images = await self._extract_from_pdf(file_path)
        elif file_extension in ['.jpg', '.jpeg', '.png']:
            text_content = await self._extract_from_image(file_path, language)
            images = [file_path]
        elif file_extension in ['.docx', '.doc']:
            text_content = await self._extract_from_docx(file_path)
            images = []
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")

        # Process with LLM for structured extraction
        structured_data = await self._extract_structured_data(text_content, language)

        # Enhance with NLP if available
        if self.nlp_models.get(language):
            enhanced_data = await self._enhance_with_nlp(text_content, structured_data, language)
            structured_data.update(enhanced_data)

        return structured_data

    async def _extract_from_pdf(self, file_path: Path) -> tuple[str, List[Path]]:
        """Extract text and images from PDF"""
        doc = fitz.open(file_path)
        text_content = ""
        images = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text_content += page.get_text()

            # Extract images if they contain important visual CV elements
            image_list = page.get_images()
            for img_index, img in enumerate(image_list):
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)
                if pix.n < 5:  # GRAY or RGB
                    img_path = f"temp_cv_image_{page_num}_{img_index}.png"
                    pix.save(img_path)
                    images.append(Path(img_path))
                pix = None

        doc.close()
        return text_content, images

    async def _extract_from_image(self, file_path: Path, language: str) -> str:
        """Extract text from image using vision model"""
        with open(file_path, 'rb') as f:
            image_data = f.read()

        prompt_templates = {
            "en": "Extract all text content from this CV/resume image. Maintain the structure and formatting.",
            "pl": "Wyciągnij całą treść tekstową z tego obrazu CV. Zachowaj strukturę i formatowanie.",
            "de": "Extrahiere den gesamten Textinhalt aus diesem Lebenslauf-Bild. Behalte die Struktur und Formatierung bei."
        }

        text_content = await self.vision_processor.analyze_image(
            image_data,
            prompt_templates.get(language, prompt_templates["en"])
        )

        return text_content

    async def _extract_from_docx(self, file_path: Path) -> str:
        """Extract text from DOCX file"""
        try:
            import docx
            doc = docx.Document(file_path)
            text_content = ""
            for paragraph in doc.paragraphs:
                text_content += paragraph.text + "\n"
            return text_content
        except ImportError:
            logger.error("python-docx not installed. Cannot process DOCX files.")
            return ""

    async def _extract_structured_data(self, text_content: str, language: str) -> Dict:
        """Extract structured data using LLM"""

        prompts = {
            "en": """
Extract the following information from this CV/resume text and format as JSON:

{
    "personal_info": {
        "name": "Full name",
        "email": "email@example.com",
        "phone": "+1234567890",
        "location": "City, Country",
        "linkedin": "LinkedIn URL",
        "website": "Personal website"
    },
    "professional_summary": "Brief professional summary",
    "work_experience": [
        {
            "position": "Job title",
            "company": "Company name",
            "location": "City, Country", 
            "start_date": "YYYY-MM",
            "end_date": "YYYY-MM or Present",
            "description": "Job description and achievements"
        }
    ],
    "education": [
        {
            "degree": "Degree type and field",
            "institution": "University/School name",
            "location": "City, Country",
            "graduation_date": "YYYY-MM",
            "gpa": "GPA if mentioned"
        }
    ],
    "skills": {
        "technical": ["skill1", "skill2"],
        "languages": ["English (Native)", "Spanish (Fluent)"],
        "soft_skills": ["skill1", "skill2"]
    },
    "certifications": ["Certification name - Year"],
    "projects": [
        {
            "name": "Project name",
            "description": "Project description",
            "technologies": ["tech1", "tech2"],
            "url": "Project URL if available"
        }
    ]
}

CV Text:
""",
            "pl": """
Wyciągnij następujące informacje z tego tekstu CV i sformatuj jako JSON:

{
    "personal_info": {
        "name": "Imię i nazwisko",
        "email": "email@example.com", 
        "phone": "+48123456789",
        "location": "Miasto, Kraj",
        "linkedin": "URL LinkedIn",
        "website": "Strona osobista"
    },
    "professional_summary": "Krótkie podsumowanie zawodowe",
    "work_experience": [
        {
            "position": "Stanowisko",
            "company": "Nazwa firmy",
            "location": "Miasto, Kraj",
            "start_date": "RRRR-MM",
            "end_date": "RRRR-MM lub Obecnie", 
            "description": "Opis pracy i osiągnięcia"
        }
    ],
    "education": [
        {
            "degree": "Rodzaj i kierunek studiów",
            "institution": "Nazwa uczelni",
            "location": "Miasto, Kraj",
            "graduation_date": "RRRR-MM",
            "gpa": "Średnia jeśli podana"
        }
    ],
    "skills": {
        "technical": ["umiejętność1", "umiejętność2"],
        "languages": ["Polski (Ojczysty)", "Angielski (Płynny)"],
        "soft_skills": ["umiejętność1", "umiejętność2"]
    },
    "certifications": ["Nazwa certyfikatu - Rok"],
    "projects": [
        {
            "name": "Nazwa projektu",
            "description": "Opis projektu", 
            "technologies": ["tech1", "tech2"],
            "url": "URL projektu jeśli dostępny"
        }
    ]
}

Tekst CV:
""",
            "de": """
Extrahiere die folgenden Informationen aus diesem Lebenslauf-Text und formatiere als JSON:

{
    "personal_info": {
        "name": "Vor- und Nachname",
        "email": "email@example.com",
        "phone": "+49123456789", 
        "location": "Stadt, Land",
        "linkedin": "LinkedIn URL",
        "website": "Persönliche Website"
    },
    "professional_summary": "Kurze berufliche Zusammenfassung",
    "work_experience": [
        {
            "position": "Position",
            "company": "Firmenname",
            "location": "Stadt, Land",
            "start_date": "JJJJ-MM",
            "end_date": "JJJJ-MM oder Aktuell",
            "description": "Stellenbeschreibung und Erfolge"
        }
    ],
    "education": [
        {
            "degree": "Abschluss und Fachrichtung", 
            "institution": "Universität/Schule",
            "location": "Stadt, Land",
            "graduation_date": "JJJJ-MM",
            "gpa": "Note falls erwähnt"
        }
    ],
    "skills": {
        "technical": ["Fähigkeit1", "Fähigkeit2"],
        "languages": ["Deutsch (Muttersprache)", "Englisch (Fließend)"],
        "soft_skills": ["Fähigkeit1", "Fähigkeit2"]
    },
    "certifications": ["Zertifikat - Jahr"],
    "projects": [
        {
            "name": "Projektname",
            "description": "Projektbeschreibung",
            "technologies": ["tech1", "tech2"], 
            "url": "Projekt URL falls verfügbar"
        }
    ]
}

Lebenslauf Text:
"""
        }

        prompt = prompts.get(language, prompts["en"]) + text_content

        structured_data = await self.llm_client.generate(
            prompt,
            model="mistral:7b",
            response_format="json"
        )

        return structured_data

    async def _enhance_with_nlp(self, text_content: str, structured_data: Dict, language: str) -> Dict:
        """Enhance extraction with spaCy NLP"""
        if not self.nlp_models.get(language):
            return {}

        nlp = self.nlp_models[language]
        doc = nlp(text_content)
        
        enhanced_data = {
            "skills": {
                "technical": list(set(structured_data.get("skills", {}).get("technical", []) + 
                                 [ent.text for ent in doc.ents if ent.label_ in ["TECH", "SKILL"]]))
            }
        }
        
        return enhanced_data
        
    async def analyze_text(self, cv_text: str, language: str = "en") -> Dict:
        """
        Analyze CV text and extract structured information.
        
        Args:
            cv_text: Raw text content of the CV
            language: Language code (default: "en")
            
        Returns:
            dict: Structured information extracted from the CV
        """
        if not cv_text or not isinstance(cv_text, str):
            return {"error": "Invalid CV text provided"}
            
        try:
            # Process with LLM for structured extraction
            structured_data = await self._extract_structured_data(cv_text, language)
            
            # Enhance with NLP if available
            if self.nlp_models.get(language):
                enhanced_data = await self._enhance_with_nlp(cv_text, structured_data, language)
                structured_data.update(enhanced_data)
                
            return structured_data
            
        except Exception as e:
            logger.error(f"Error analyzing CV text: {str(e)}")
            return {"error": f"Failed to analyze CV: {str(e)}"}