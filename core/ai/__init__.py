"""
Core AI module for CV parsing and analysis.
"""
from .cv_parser import CVParser
from .form_analyzer import FormAnalyzer
from .llm_client import LLMClient
from .vision_processor import VisionProcessor

# Initialize default instances
cv_parser = CVParser()
form_analyzer = FormAnalyzer()
llm_client = LLMClient()
vision_processor = VisionProcessor()

def analyze_cv(cv_text: str, language: str = "en") -> dict:
    """
    Analyze CV text and extract structured information.
    
    Args:
        cv_text: Raw text content of the CV
        language: Language code (default: "en")
        
    Returns:
        dict: Structured information extracted from the CV
    """
    # Use the global parser instance
    return asyncio.run(cv_parser.analyze_text(cv_text, language))

__all__ = [
    'analyze_cv',
    'CVParser',
    'FormAnalyzer',
    'LLMClient',
    'VisionProcessor',
    'cv_parser',
    'form_analyzer',
    'llm_client',
    'vision_processor'
]