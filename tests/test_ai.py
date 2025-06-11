"""
Tests for AI functionality.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Test data
TEST_CV = """John Doe
Senior Software Engineer
5+ years of experience in Python and FastAPI"""

@pytest.fixture
def mock_llm_client():
    """Fixture to mock the LLMClient."""
    with patch('core.ai.llm_client.LLMClient') as mock_client:
        yield mock_client()

@pytest.mark.asyncio
async def test_cv_analysis(mock_llm_client):
    """Test CV analysis with mock LLM response."""
    from core.ai import analyze_cv
    
    # Mock the analyze_cv method
    mock_llm_client.analyze_cv = AsyncMock(return_value={
        "skills": ["Python", "FastAPI"],
        "experience": 5,
        "role": "Senior Software Engineer"
    })
    
    result = await analyze_cv(TEST_CV)
    
    # Verify the result
    assert isinstance(result, dict)
    assert "skills" in result
    assert "Python" in result["skills"]
    assert result["experience"] == 5
    assert result["role"] == "Senior Software Engineer"
    
    # Verify the method was called with the correct arguments
    mock_llm_client.analyze_cv.assert_awaited_once_with(TEST_CV)

@pytest.mark.asyncio
async def test_ai_error_handling(mock_llm_client):
    """Test error handling in AI functions."""
    from core.ai import analyze_cv
    
    # Simulate an error in the LLM client
    mock_llm_client.analyze_cv = AsyncMock(side_effect=Exception("API Error"))
    
    # Test that the exception is properly propagated
    with pytest.raises(Exception) as exc_info:
        await analyze_cv(TEST_CV)
    assert "API Error" in str(exc_info.value)

@pytest.mark.asyncio
@pytest.mark.parametrize("input_text, expected_type", [
    ("5+ years of experience", dict),
    ("", dict),  # Empty input
    (None, dict),  # None input
])
async def test_analyze_cv_edge_cases(mock_llm_client, input_text, expected_type):
    """Test edge cases for CV analysis."""
    from core.ai import analyze_cv
    
    # Mock a successful but empty response
    mock_llm_client.analyze_cv = AsyncMock(return_value={"skills": [], "experience": 0})
    
    result = await analyze_cv(input_text)
    assert isinstance(result, expected_type)
    
    # Verify the method was called with the correct arguments
    if input_text is not None:
        mock_llm_client.analyze_cv.assert_awaited_once_with(input_text)
    else:
        mock_llm_client.analyze_cv.assert_awaited_once_with("")
