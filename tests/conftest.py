"""
Test configuration and fixtures for the coBoarding test suite.
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# Add the project root to the Python path first
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock hcaptcha_challenger.agents before any other imports
mock_agents = MagicMock()
mock_agents.AgentT = MagicMock()

# Patch sys.modules before any other imports
sys.modules['hcaptcha_challenger.agents'] = mock_agents

# Now import the rest of the dependencies
import pytest
from fastapi.testclient import TestClient

# Mock environment variables for testing
os.environ.update({
    "REDIS_URL": "redis://test-redis:6379/0",
    "OLLAMA_BASE_URL": "http://test-ollama:11434",
    "SECRET_KEY": "test-secret-key",
    "API_KEY": "test-api-key",
    "SUPPORTED_LANGUAGES": "en,pl,de",
    "ENVIRONMENT": "test",
    "LOG_LEVEL": "INFO"
})

@pytest.fixture(scope="module")
def test_client():
    """Create a test client for the FastAPI application."""
    # Import here to ensure environment variables are set first
    from api.main import app
    with TestClient(app) as client:
        yield client

@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    with patch('redis.Redis') as mock_redis:
        yield mock_redis

@pytest.fixture
def mock_ollama():
    """Create a mock Ollama client."""
    with patch('requests.post') as mock_post:
        mock_response = Mock()
        mock_response.json.return_value = {"response": "test response"}
        mock_post.return_value = mock_response
        yield mock_post

@pytest.fixture
def test_data_dir():
    """Return the path to the test data directory."""
    return os.path.join(os.path.dirname(__file__), 'data')

@pytest.fixture(scope="module")
async def mock_playwright():
    """Create a mock Playwright browser instance."""
    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    
    # Set up the mock chain
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page
    
    # Create a mock Playwright instance with proper async support
    mock_playwright_instance = AsyncMock()
    mock_playwright_instance.start.return_value = mock_playwright_instance
    mock_playwright_instance.chromium.launch.return_value = mock_browser
    
    # Create a coroutine function that returns the mock Playwright instance
    async def mock_async_playwright():
        return mock_playwright_instance
    
    # Patch the async_playwright function
    with patch('core.automation.async_playwright', new=mock_async_playwright):
        yield mock_browser, mock_context, mock_page
