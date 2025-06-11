"""
Tests for browser automation functionality.
"""
import asyncio
import os
import sys
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from pathlib import Path

# Mock hcaptcha_challenger.agents before any other imports
import builtins
from unittest.mock import MagicMock

# Create a mock for hcaptcha_challenger.agents
mock_agents = MagicMock()
AgentT = MagicMock()
mock_agents.AgentT = AgentT

# Patch sys.modules before any other imports
import sys
sys.modules['hcaptcha_challenger.agents'] = mock_agents

# Mock environment variables for testing
os.environ.update({
    "ENVIRONMENT": "test",
    "LOG_LEVEL": "DEBUG",
    "BROWSER_HEADLESS": "true"
})

# Test data
TEST_URL = "https://example.com"
TEST_SELECTOR = ".job-listing"
TEST_OUTPUT_DIR = "/tmp/test_output"

@pytest.fixture
def mock_playwright():
    """Fixture to mock Playwright browser, context, and page."""
    # Create mock objects with proper async support
    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    
    # Set up the mock chain with proper async return values
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_context.new_page = AsyncMock(return_value=mock_page)
    
    # Create a mock Playwright instance with proper async support
    mock_playwright_instance = MagicMock()
    mock_playwright_instance.chromium = MagicMock()
    mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser)
    
    # Create a mock async_playwright function that returns a mock with start()
    async def mock_async_playwright():
        mock = MagicMock()
        mock.start = AsyncMock(return_value=mock_playwright_instance)
        return mock
    
    # Patch the async_playwright function in the stealth_browser module
    with patch('core.automation.stealth_browser.async_playwright', new=mock_async_playwright):
        yield mock_browser, mock_context, mock_page

@pytest.mark.asyncio
async def test_browser_initialization(mock_playwright):
    """Test browser initialization."""
    from core.automation import BrowserAutomation
    
    mock_browser, mock_context, mock_page = mock_playwright
    
    # Create browser instance and test initialization
    browser = BrowserAutomation()
    
    # Mock the _get_random_user_agent method to return a test user agent
    with patch.object(browser, '_get_random_user_agent', return_value="test-user-agent"):
        await browser.initialize()
    
    # Verify the browser was initialized correctly
    assert browser.browser is not None
    assert browser.context is not None
    assert browser.page is not None
    
    # Verify the correct methods were called with expected arguments
    mock_browser.new_context.assert_awaited_once_with(
        viewport={'width': 1920, 'height': 1080},
        user_agent="test-user-agent",
        locale='en-US',
        permissions=['clipboard-read', 'clipboard-write']
    )
    mock_context.new_page.assert_awaited_once()

@pytest.mark.asyncio
async def test_navigate_and_extract(mock_playwright):
    """Test page navigation and content extraction."""
    from core.automation import BrowserAutomation
    
    mock_browser, mock_context, mock_page = mock_playwright
    
    # Configure the mock page
    mock_element = AsyncMock()
    mock_element.inner_text.return_value = "Test Job"
    mock_page.wait_for_selector.return_value = mock_element
    
    # Create and initialize browser instance
    browser = BrowserAutomation()
    browser.browser = mock_browser
    browser.context = mock_context
    browser.page = mock_page
    
    # Test the extract_content method
    content = await browser.extract_content(TEST_SELECTOR)
    
    # Verify the content extraction
    mock_page.wait_for_selector.assert_awaited_once_with(TEST_SELECTOR, timeout=60000)
    mock_element.inner_text.assert_awaited_once()
    assert content == "Test Job"

@pytest.mark.asyncio
async def test_screenshot_capture(mock_playwright, tmp_path):
    """Test screenshot capture functionality."""
    from core.automation import BrowserAutomation
    from pathlib import Path
    
    mock_browser, mock_context, mock_page = mock_playwright
    
    # Create a temporary directory for testing
    test_dir = tmp_path / "screenshots"
    test_dir.mkdir()
    
    # Create a test file with .png suffix
    test_file = test_dir / "test_screenshot.png"
    test_file.touch()
    
    # Configure the mock screenshot to not return anything (method is void)
    mock_page.screenshot.return_value = None
    
    # Create and initialize browser instance
    browser = BrowserAutomation()
    browser.browser = mock_browser
    browser.context = mock_context
    browser.page = mock_page
    
    # Test the capture_screenshot method
    output_path = await browser.capture_screenshot(str(test_file))
    
    # Verify the screenshot was taken and saved
    mock_page.screenshot.assert_awaited_once_with(
        path=str(test_file.absolute()),
        full_page=True
    )
    
    # Verify the output path is a Path object with .png suffix
    assert isinstance(output_path, Path)
    assert output_path.suffix == '.png'
    assert output_path == test_file.absolute()

def test_selector_validation():
    """Test CSS selector validation."""
    from core.automation import validate_selector
    
    assert validate_selector(".valid-class") is True
    assert validate_selector("#valid-id") is True
    assert validate_selector("div > p") is True
    
    with pytest.raises(ValueError):
        validate_selector("invalid selector!")
