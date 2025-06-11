"""
Core AI module for CV parsing and analysis.
"""
import asyncio
import logging
from .cv_parser import CVParser
from .form_analyzer import FormAnalyzer
from .llm_client import LLMClient
from .vision_processor import VisionProcessor

# Configure logger
logger = logging.getLogger(__name__)

# Initialize default instances
cv_parser = CVParser()
form_analyzer = FormAnalyzer()
llm_client = LLMClient()
vision_processor = VisionProcessor()

async def analyze_cv(cv_text: str, language: str = "en") -> dict:
    """
    Analyze CV text and extract structured information.
    
    Args:
        cv_text: Raw text content of the CV
        language: Language code (default: "en")
        
    Returns:
        dict: Structured information extracted from the CV
        
    Raises:
        Exception: If there's an error during analysis
    """
    try:
        # First try using the LLM client
        result = await llm_client.analyze_cv(cv_text)
        if result and not result.get('error'):
            return result
            
        # Fall back to CV parser if LLM fails
        logger.warning("Falling back to CV parser")
        return await cv_parser.analyze_text(cv_text, language=language)
        
    except Exception as e:
        logger.error(f"Error analyzing CV: {e}")
        raise Exception(f"Failed to analyze CV: {str(e)}")

def analyze_cv_sync(cv_text: str, language: str = "en") -> dict:
    """
    Synchronous wrapper for CV analysis.
    
    Args:
        cv_text: Raw text content of the CV
        language: Language code (default: "en")
        
    Returns:
        dict: Structured information extracted from the CV
    """
    return asyncio.run(analyze_cv(cv_text, language))

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