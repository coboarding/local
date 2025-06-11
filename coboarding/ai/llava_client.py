"""
LLaVA client for visual analysis of web pages to detect file upload elements.
"""
import base64
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import httpx
from PIL import Image
import io

logger = logging.getLogger(__name__)

class LLaVAClient:
    """Client for interacting with LLaVA visual language model."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        """Initialize the LLaVA client.
        
        Args:
            base_url: Base URL for the Ollama API (default: http://localhost:11434)
        """
        self.base_url = base_url
        self.model_name = "llava"
        self.timeout = 60  # seconds
    
    async def analyze_image(self, image_path: str, prompt: str) -> Dict[str, Any]:
        """Analyze an image using LLaVA.
        
        Args:
            image_path: Path to the image file to analyze
            prompt: The prompt to use for analysis
            
        Returns:
            Dict containing the analysis results
        """
        try:
            # Read and encode the image
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Convert to bytes
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG")
                img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            # Prepare the request payload
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "images": [img_str],
                "stream": False
            }
            
            # Make the request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                result = response.json()
                return {
                    "response": result.get("response", ""),
                    "model": result.get("model", ""),
                    "created_at": result.get("created_at", "")
                }
                
        except Exception as e:
            logger.error(f"Error analyzing image with LLaVA: {str(e)}")
            return {"error": str(e)}
    
    async def detect_upload_elements(self, screenshot_path: str) -> List[Dict[str, Any]]:
        """Detect file upload elements in a screenshot.
        
        Args:
            screenshot_path: Path to the screenshot file
            
        Returns:
            List of detected upload elements with their properties
        """
        prompt = """
        Analyze this web page screenshot and identify any file upload elements.
        Look for:
        1. File input fields (type="file")
        2. Buttons with text like 'Upload', 'Choose File', 'Browse', 'Hochladen', 'Datei auswählen'
        3. Drag and drop areas
        4. Icons that might indicate file upload functionality
        
        For each potential upload element, provide:
        - A description of the element
        - Its position on the page (top-left, center, etc.)
        - Any visible text or labels near it
        - Your confidence level (high/medium/low)
        
        Format your response as a JSON list of objects.
        """
        
        try:
            result = await self.analyze_image(screenshot_path, prompt)
            if "error" in result:
                logger.warning(f"LLaVA analysis failed: {result['error']}")
                return []
                
            # Try to parse the response as JSON
            try:
                import json
                return json.loads(result["response"])
            except json.JSONDecodeError:
                logger.warning("Failed to parse LLaVA response as JSON")
                return []
                
        except Exception as e:
            logger.error(f"Error in detect_upload_elements: {str(e)}")
            return []

# Create a default instance for easy importing
default_llava_client = LLaVAClient()
