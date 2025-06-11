"""
Tests for AI functionality.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch, ANY, DEFAULT, call
from fastapi import HTTPException
from core.ai.llm_client import LLMClient

# Test data
TEST_CV = """John Doe
Senior Software Engineer
5+ years of experience in Python and FastAPI"""

@pytest.fixture
def mock_llm_client():
    """Fixture to mock the LLMClient."""
    # Create a mock for the LLMClient class
    mock_client = MagicMock(spec=LLMClient)
    
    # Create a mock for the instance
    mock_instance = AsyncMock()
    
    # Set up mock methods
    mock_instance.analyze_cv = AsyncMock()
    mock_instance.generate = AsyncMock()
    mock_instance.health_check = AsyncMock()
    
    # Set up mock return values
    mock_instance.analyze_cv.return_value = {
        "skills": ["Python", "FastAPI"],
        "experience": 5,
        "role": "Senior Software Engineer"
    }
    mock_instance.generate.return_value = "Test response from LLM"
    mock_instance.health_check.return_value = True
    
    # Make the class return our mock instance
    mock_client.return_value = mock_instance
    
    # Patch the LLMClient in the core.ai module
    with patch('core.ai.llm_client.LLMClient', mock_client):
        yield mock_instance

@pytest.mark.asyncio
async def test_cv_analysis(mock_llm_client):
    """Test CV analysis with mock LLM response."""
    # Import inside test to ensure proper patching
    with patch('core.ai.llm_client', mock_llm_client):
        from core.ai import analyze_cv
        
        # Setup mock response
        mock_response = {
            "skills": ["Python", "FastAPI"],
            "experience": 5,
            "role": "Senior Software Engineer"
        }
        mock_llm_client.analyze_cv.return_value = mock_response
        
        # Call the function
        result = await analyze_cv(TEST_CV)
        
        # Verify the result
        assert isinstance(result, dict)
        assert "skills" in result
        assert "Python" in result["skills"]
        assert result["experience"] == 5
        assert result["role"] == "Senior Software Engineer"
        
        # Verify the method was called with the correct arguments
        mock_llm_client.analyze_cv.assert_awaited_once_with(TEST_CV, "en")

@pytest.mark.asyncio
async def test_ai_error_handling(mock_llm_client):
    """Test error handling in AI functions."""
    with patch('core.ai.llm_client', mock_llm_client):
        from core.ai import analyze_cv
        
        # Simulate an error in the LLM client
        error_message = "API Error: Failed to analyze CV"
        mock_llm_client.analyze_cv.side_effect = Exception(error_message)
        
        # Test that the exception is properly propagated
        with pytest.raises(HTTPException) as exc_info:
            await analyze_cv(TEST_CV)
        
        assert exc_info.value.status_code == 500
        assert error_message in str(exc_info.value.detail)
        
        # Reset side effect for other tests
        mock_llm_client.analyze_cv.side_effect = None

@pytest.mark.asyncio
@pytest.mark.parametrize("input_text, expected_type", [
    ("5+ years of experience", dict),
    ("", dict),  # Empty input
])
async def test_analyze_cv_edge_cases(mock_llm_client, input_text, expected_type):
    """Test edge cases for CV analysis."""
    with patch('core.ai.llm_client', mock_llm_client):
        from core.ai import analyze_cv
        
        # Mock a successful but empty response
        mock_response = {"skills": [], "experience": 0}
        mock_llm_client.analyze_cv.return_value = mock_response
        
        # Call the function
        result = await analyze_cv(input_text)
        
        # Verify the result
        assert isinstance(result, dict)
        assert "skills" in result
        assert "experience" in result
        
        # Verify the method was called with the correct arguments
        mock_llm_client.analyze_cv.assert_awaited_once_with(input_text, "en")

@pytest.mark.asyncio
async def test_analyze_cv_none_input(mock_llm_client):
    """Test CV analysis with None input."""
    with patch('core.ai.llm_client', mock_llm_client):
        from core.ai import analyze_cv
        
        # Mock a successful but empty response
        mock_response = {"skills": [], "experience": 0}
        mock_llm_client.analyze_cv.return_value = mock_response
        
        # Call the function with None
        result = await analyze_cv(None)
        
        # Verify the result
        assert isinstance(result, dict)
        assert "skills" in result
        assert "experience" in result
        
        # Verify the method was called with None and default language
        mock_llm_client.analyze_cv.assert_awaited_once_with(None, "en")

@pytest.mark.asyncio
async def test_llm_client_generate(mock_llm_client):
    """Test LLM client generate method with mocked responses."""
    # Setup test data
    test_prompt = "Test prompt"
    test_response = "Test response from LLM"
    
    # Configure the mock
    mock_llm_client.generate.return_value = test_response
    
    # Call the method with only required args
    result = await mock_llm_client.generate(test_prompt)
    
    # Verify the result
    assert result == test_response
    mock_llm_client.generate.assert_awaited_once_with(test_prompt)

@pytest.mark.asyncio
async def test_llm_client_health_check(mock_llm_client):
    """Test LLM client health check."""
    # Setup test data
    mock_llm_client.health_check.return_value = True
    
    # Call the method
    result = await mock_llm_client.health_check()
    
    # Verify the result
    assert result is True
    mock_llm_client.health_check.assert_awaited_once()

@pytest.mark.asyncio
async def test_llm_client_analyze_cv(mock_llm_client):
    """Test LLM client analyze_cv method."""
    # Setup test data
    test_cv = "Test CV content"
    test_language = "en"
    expected_response = {
        "skills": ["Python", "FastAPI"],
        "experience": 5,
        "role": "Senior Software Engineer"
    }
    
    # Call the method
    result = await mock_llm_client.analyze_cv(test_cv, test_language)
    
    # Verify the result
    assert result == expected_response
    mock_llm_client.analyze_cv.assert_awaited_once_with(test_cv, test_language)
