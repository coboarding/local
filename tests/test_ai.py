"""
Tests for AI functionality.
"""
import pytest
from unittest.mock import Mock, patch

# Test data
TEST_CV = """John Doe
Senior Software Engineer
5+ years of experience in Python and FastAPI"""

def test_cv_analysis(mock_ollama):
    """Test CV analysis with mock Ollama response."""
    from core.ai import analyze_cv
    
    # Mock Ollama response
    mock_response = {
        "response": "{\"skills\": [\"Python\", \"FastAPI\"], \"experience\": 5, \"role\": \"Senior Software Engineer\"}"
    }
    mock_ollama.return_value.json.return_value = mock_response
    
    result = analyze_cv(TEST_CV)
    
    assert isinstance(result, dict)
    assert "skills" in result
    assert "Python" in result["skills"]
    assert result["experience"] == 5
    assert result["role"] == "Senior Software Engineer"

def test_ai_error_handling(mock_ollama):
    """Test error handling in AI functions."""
    from core.ai import analyze_cv
    
    # Simulate API error
    mock_ollama.side_effect = Exception("API Error")
    
    with pytest.raises(Exception) as exc_info:
        analyze_cv(TEST_CV)
    assert "API Error" in str(exc_info.value)

@pytest.mark.parametrize("input_text, expected_type", [
    ("5+ years of experience", dict),
    ("", dict),  # Empty input
    (None, dict),  # None input
])
def test_analyze_cv_edge_cases(mock_ollama, input_text, expected_type):
    """Test edge cases for CV analysis."""
    from core.ai import analyze_cv
    
    # Mock successful but empty response
    mock_ollama.return_value.json.return_value = {"response": "{}"}
    
    result = analyze_cv(input_text)
    assert isinstance(result, expected_type)
