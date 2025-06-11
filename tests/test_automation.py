"""
Tests for browser automation functionality.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

# Test data
TEST_URL = "https://example.com"
TEST_SELECTOR = ".job-listing"
TEST_OUTPUT_DIR = "/tmp/test_output"

@pytest.mark.asyncio
async def test_browser_initialization():
    """Test browser initialization."""
    from core.automation import BrowserAutomation
    
    with patch('playwright.async_api.async_playwright') as mock_playwright:
        # Setup mock
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        mock_playwright.return_value.__aenter__.return_value.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value.__aenter__.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        # Test
        async with BrowserAutomation() as browser:
            assert browser is not None
            mock_playwright.return_value.__aenter__.assert_called_once()
            mock_browser.new_context.assert_called_once()

@pytest.mark.asyncio
async def test_navigate_and_extract():
    """Test page navigation and content extraction."""
    from core.automation import BrowserAutomation
    
    with patch('core.automation.BrowserAutomation._init_browser') as mock_init:
        # Setup mock browser and page
        mock_page = AsyncMock()
        mock_page.content.return_value = "<div class='job-listing'>Test Job</div>"
        
        browser = BrowserAutomation()
        browser.page = mock_page
        
        # Test
        content = await browser.extract_content(TEST_URL, TEST_SELECTOR)
        
        # Assertions
        mock_page.goto.assert_called_once_with(TEST_URL, timeout=60000)
        mock_page.wait_for_selector.assert_called_once_with(TEST_SELECTOR, timeout=10000)
        assert "Test Job" in content

@pytest.mark.asyncio
async def test_screenshot_capture():
    """Test screenshot capture functionality."""
    from core.automation import BrowserAutomation
    
    with patch('core.automation.BrowserAutomation._init_browser') as mock_init, \
         patch('pathlib.Path.mkdir') as mock_mkdir:
        
        # Setup mock
        mock_page = AsyncMock()
        browser = BrowserAutomation()
        browser.page = mock_page
        
        # Test
        output_path = await browser.capture_screenshot(TEST_URL, TEST_OUTPUT_DIR)
        
        # Assertions
        mock_page.goto.assert_called_once_with(TEST_URL, timeout=60000)
        mock_page.screenshot.assert_called_once()
        assert str(output_path).endswith('.png')
        assert TEST_OUTPUT_DIR in str(output_path)

def test_selector_validation():
    """Test CSS selector validation."""
    from core.automation import validate_selector
    
    assert validate_selector(".valid-class") is True
    assert validate_selector("#valid-id") is True
    assert validate_selector("div > p") is True
    
    with pytest.raises(ValueError):
        validate_selector("invalid selector!")
