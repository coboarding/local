"""
Test script for LLaVA client.
"""
import asyncio
import logging
import os
from coboarding.ai.llava_client import LLaVAClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_llava_client():
    """Test the LLaVA client with a simple image analysis."""
    # Create a simple test image
    from PIL import Image, ImageDraw
    
    # Create a simple image with text
    img = Image.new('RGB', (300, 200), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((10, 10), "Test Image for LLaVA", fill=(0, 0, 0))
    
    # Save the test image
    test_image_path = "test_image.png"
    img.save(test_image_path)
    logger.info(f"Created test image at {os.path.abspath(test_image_path)}")
    
    # Initialize the LLaVA client
    llava = LLaVAClient()
    
    # Test prompt
    prompt = "What text is in this image?"
    
    try:
        logger.info("Testing LLaVA client...")
        result = await llava.analyze_image(test_image_path, prompt)
        
        if "error" in result:
            logger.error(f"Error from LLaVA: {result['error']}")
        else:
            logger.info("LLaVA response:")
            print(result.get("response", "No response"))
            
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
    finally:
        # Clean up
        if os.path.exists(test_image_path):
            os.remove(test_image_path)

if __name__ == "__main__":
    asyncio.run(test_llava_client())
