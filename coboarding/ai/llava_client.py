"""
LLaVA client for visual analysis of web pages to detect file upload elements.
"""
import base64
import logging
import io
import json
import os
from typing import Dict, List, Any, Optional, Union
from PIL import Image, UnidentifiedImageError
import httpx

logger = logging.getLogger(__name__)

class LLaVAClient:
    """Client for interacting with LLaVA visual language model."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        """Initialize the LLaVA client.
        
        Args:
            base_url: Base URL for the Ollama API (default: http://localhost:11434)
        """
        self.base_url = base_url.rstrip('/')
        self.model_name = "llava:7b"  # Specify the exact model name with tag
        self.timeout = 300  # Increase timeout for image processing
    
    async def _process_image(self, image_path: str) -> str:
        """Process and encode an image to base64.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Base64 encoded image string
            
        Raises:
            FileNotFoundError: If image file doesn't exist
            UnidentifiedImageError: If image cannot be identified
            Exception: For other image processing errors
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
            
        try:
            with Image.open(image_path) as img:
                # Convert image to RGB if it's not already
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Save image to bytes buffer
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG')
                
                # Encode image to base64
                return base64.b64encode(buffer.getvalue()).decode('utf-8')
                
        except UnidentifiedImageError as e:
            logger.error(f"Could not identify image file: {image_path}")
            raise
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {str(e)}")
            raise
    
    async def analyze_image(self, image_path: str, prompt: str) -> Dict[str, Any]:
        """Analyze an image using LLaVA via Ollama CLI.
        
        Args:
            image_path: Path to the image file to analyze
            prompt: The prompt to use for analysis
            
        Returns:
            Dict containing the analysis results with keys:
            - response: The model's response text
            - model: The model used for analysis
            - error: Error message if any
        """
        try:
            # Convert image to JPEG if needed
            with Image.open(image_path) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Create a temporary file for the converted image
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_img:
                    img.save(tmp_img, format='JPEG')
                    tmp_img_path = tmp_img.name
            
            try:
                # Build the command
                cmd = [
                    'ollama', 'run',
                    '--format', 'json',
                    self.model_name,
                    f'[img-1] {prompt}'
                ]
                
                # Run the command with the image as input
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                
                # Read the image data
                with open(tmp_img_path, 'rb') as f:
                    image_data = f.read()
                
                # Send the image data to the process
                stdout, stderr = await process.communicate(input=image_data)
                
                # Clean up the temporary file
                try:
                    os.unlink(tmp_img_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file {tmp_img_path}: {e}")
                
                if process.returncode != 0:
                    error_msg = stderr.decode('utf-8') if stderr else 'Unknown error'
                    return {
                        'response': '',
                        'model': self.model_name,
                        'error': f'Ollama CLI error: {error_msg}'
                    }
                
                # Parse the JSON response
                response_text = stdout.decode('utf-8')
                try:
                    response_data = json.loads(response_text)
                    if isinstance(response_data, dict):
                        return {
                            "response": response_data.get("response", ""),
                            "model": response_data.get("model", self.model_name),
                            "created_at": response_data.get("created_at", ""),
                            "success": True
                        }
                except json.JSONDecodeError:
                    # Return the raw response if not JSON
                    return {
                        "response": response_text,
                        "model": self.model_name,
                        "created_at": "",
                        "success": True
                    }
                
            except httpx.HTTPStatusError as e:
                error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
                logger.error(error_msg)
                raise
            except Exception as e:
                logger.error(f"Error in analyze_image: {str(e)}", exc_info=True)
                raise
                
        except Exception as e:
            logger.error(f"Error analyzing image with LLaVA: {str(e)}")
            return {"error": str(e), "success": False}
    
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
