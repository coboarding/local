"""
Automation API router for browser automation tasks.
"""
from fastapi import APIRouter, HTTPException, Depends, status, Body
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
import logging
import asyncio
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime

# Import browser automation components
from core.automation import BrowserAutomation, validate_selector

# Create the router
router = APIRouter(
    prefix="/automation",
    tags=["automation"],
    responses={404: {"description": "Not found"}},
)

# Configure logging
logger = logging.getLogger(__name__)


# Models
class NavigationRequest(BaseModel):
    """Request model for navigation."""
    url: HttpUrl
    wait_until: str = "load"  # load, domcontentloaded, networkidle
    timeout: int = 30000  # milliseconds
    wait_for_selector: Optional[str] = None

class ClickRequest(BaseModel):
    """Request model for clicking an element."""
    selector: str
    button: str = "left"  # left, right, middle
    click_count: int = 1
    delay: int = 0  # milliseconds

class FillFormRequest(BaseModel):
    """Request model for filling a form."""
    fields: Dict[str, str] = Field(..., description="Dictionary of selectors to values")
    submit_selector: Optional[str] = None

class ExtractRequest(BaseModel):
    """Request model for extracting data from a page."""
    selectors: Dict[str, str] = Field(..., description="Dictionary of names to CSS selectors")

class ScreenshotRequest(BaseModel):
    """Request model for taking a screenshot."""
    selector: Optional[str] = None
    full_page: bool = False
    path: Optional[str] = None

# Global browser instance (for demo purposes - in production, use a proper connection pool)
browser = None

# Helper functions
async def get_browser() -> BrowserAutomation:
    """Get or create a browser instance."""
    global browser
    if browser is None or not await browser.is_connected():
        browser = BrowserAutomation()
        await browser.initialize()
    return browser

# Endpoints
@router.post("/navigate")
async def navigate(request: NavigationRequest):
    """
    Navigate to a URL.
    
    Args:
        request: Navigation request parameters
    """
    try:
        browser = await get_browser()
        
        # Validate selector if provided
        if request.wait_for_selector:
            if not validate_selector(request.wait_for_selector):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid selector: {request.wait_for_selector}"
                )
        
        await browser.navigate(
            url=str(request.url),
            wait_until=request.wait_until,
            timeout=request.timeout,
            wait_for_selector=request.wait_for_selector
        )
        
        return {"status": "success", "url": str(request.url)}
        
    except Exception as e:
        logger.error(f"Navigation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Navigation failed: {str(e)}"
        )

@router.post("/click")
async def click(request: ClickRequest):
    """
    Click an element on the page.
    
    Args:
        request: Click request parameters
    """
    try:
        if not validate_selector(request.selector):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid selector: {request.selector}"
            )
            
        browser = await get_browser()
        await browser.click(
            selector=request.selector,
            button=request.button,
            click_count=request.click_count,
            delay=request.delay
        )
        
        return {"status": "success", "action": "click", "selector": request.selector}
        
    except Exception as e:
        logger.error(f"Click error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Click failed: {str(e)}"
        )

@router.post("/fill-form")
async def fill_form(request: FillFormRequest):
    """
    Fill out a form on the page.
    
    Args:
        request: Form filling request parameters
    """
    try:
        # Validate all selectors first
        for selector in list(request.fields.keys()) + ([] if not request.submit_selector else [request.submit_selector]):
            if not validate_selector(selector):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid selector: {selector}"
                )
        
        browser = await get_browser()
        
        # Fill each field
        results = {}
        for selector, value in request.fields.items():
            await browser.fill(selector, value)
            results[selector] = "filled"
        
        # Submit form if submit_selector is provided
        if request.submit_selector:
            await browser.click(request.submit_selector)
            results["form_submitted"] = True
        
        return {
            "status": "success",
            "action": "fill_form",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Form fill error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Form fill failed: {str(e)}"
        )

@router.post("/extract")
async def extract_data(request: ExtractRequest):
    """
    Extract data from the page using CSS selectors.
    
    Args:
        request: Data extraction request parameters
    """
    try:
        # Validate all selectors first
        for name, selector in request.selectors.items():
            if not validate_selector(selector):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid selector for '{name}': {selector}"
                )
        
        browser = await get_browser()
        results = {}
        
        # Extract data for each selector
        for name, selector in request.selectors.items():
            try:
                elements = await browser.query_selector_all(selector)
                if not elements:
                    results[name] = None
                    continue
                    
                # For multiple elements, get text content
                if len(elements) > 1:
                    results[name] = [await el.text_content() for el in elements]
                else:
                    results[name] = await elements[0].text_content()
            except Exception as e:
                logger.warning(f"Failed to extract '{name}': {str(e)}")
                results[name] = None
        
        return {
            "status": "success",
            "data": results
        }
        
    except Exception as e:
        logger.error(f"Data extraction error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Data extraction failed: {str(e)}"
        )

@router.post("/screenshot")
async def take_screenshot(request: ScreenshotRequest = None):
    """
    Take a screenshot of the current page or a specific element.
    
    Args:
        request: Screenshot request parameters (optional)
    """
    try:
        if request is None:
            request = ScreenshotRequest()
            
        if request.selector and not validate_selector(request.selector):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid selector: {request.selector}"
            )
        
        browser = await get_browser()
        
        # Generate a filename if not provided
        if not request.path:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            request.path = f"screenshots/screenshot_{timestamp}.png"
        
        # Take the screenshot
        await browser.screenshot(
            path=request.path,
            selector=request.selector,
            full_page=request.full_page
        )
        
        return {
            "status": "success",
            "path": request.path,
            "selector": request.selector,
            "full_page": request.full_page
        }
        
    except Exception as e:
        logger.error(f"Screenshot error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Screenshot failed: {str(e)}"
        )

@router.get("/close")
async def close_browser():
    """Close the browser instance."""
    global browser
    try:
        if browser:
            await browser.close()
            browser = None
        return {"status": "success", "message": "Browser closed"}
    except Exception as e:
        logger.error(f"Error closing browser: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to close browser: {str(e)}"
        )
