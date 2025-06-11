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
    """Fixture to mock Playwright browser and context."""
    with patch('playwright.async_api.async_playwright') as mock_playwright:
        # Create mock browser, context, and page
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        # Set up the async context manager behavior
        async def async_context_manager():
            return mock_page
            
        mock_context.new_page.return_value = mock_page
        mock_context.__aenter__.return_value = mock_context
        mock_context.__aexit__.return_value = None
        
        mock_browser.new_context.return_value = mock_context
        mock_browser_context = AsyncMock(return_value=mock_context)
        mock_browser.new_context = mock_browser_context
        
        # Set up the async playwright instance
        mock_pw_instance = AsyncMock()
        mock_pw_instance.chromium.launch.return_value = mock_browser
        
        # Set up the async context manager for async_playwright
        mock_playwright.return_value.__aenter__.return_value = mock_pw_instance
        
        yield mock_playwright, mock_pw_instance, mock_browser, mock_context, mock_page

@pytest.mark.asyncio
async def test_browser_initialization(mock_playwright):
    """Test browser initialization with default settings."""
    mock_playwright, mock_pw_instance, mock_browser, mock_context, mock_page = mock_playwright
    
    # Patch the _get_random_user_agent method
    with patch.object(BrowserAutomation, '_get_random_user_agent', return_value='test-user-agent'):
        automation = BrowserAutomation()
        await automation.initialize()
        
        # Verify the browser was launched with the correct arguments
        mock_pw_instance.chromium.launch.assert_awaited_once_with(headless=True)
        
        # Verify the context was created with the correct arguments
        mock_browser.new_context.assert_awaited_once_with(
            user_agent='test-user-agent',
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True,
            java_script_enabled=True
        )
        
        # Verify the context was entered
        mock_context.__aenter__.assert_awaited_once()
        
        # Verify the page was created
        mock_context.new_page.assert_awaited_once()
        
        # Verify the page was set on the instance
        assert automation.page is not None
        assert automation.browser is not None
        assert automation.context is not None

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
