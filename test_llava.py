import asyncio
import logging
from coboarding.ai.llava_client import LLaVAClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_llava():
    # Create a test image with PIL
    from PIL import Image, ImageDraw
    
    # Create a simple test image
    img = Image.new('RGB', (200, 200), color='white')
    d = ImageDraw.Draw(img)
    d.text((10, 100), "Test Image", fill='black')
    test_image_path = "test_image.jpg"
    img.save(test_image_path)
    
    # Initialize the client
    client = LLaVAClient()
    
    # Test image analysis
    prompt = "What is in this image?"
    logger.info(f"Analyzing image with prompt: {prompt}")
    
    try:
        result = await client.analyze_image(test_image_path, prompt)
        logger.info(f"Analysis result: {result}")
    except Exception as e:
        logger.error(f"Error analyzing image: {e}")
    finally:
        # Clean up
        import os
        if os.path.exists(test_image_path):
            os.remove(test_image_path)

if __name__ == "__main__":
    asyncio.run(test_llava())
