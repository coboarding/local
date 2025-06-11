"""
Tests for the API endpoints.
"""
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import status

# Test data
TEST_CV = """John Doe
Senior Software Engineer
5+ years of experience in Python and FastAPI"""

TEST_JOB_DESCRIPTION = """Looking for a Senior Software Engineer with:
- 5+ years of Python experience
- Experience with FastAPI
- Knowledge of Docker and Kubernetes"""

@pytest.fixture
def mock_llm_client():
    """Fixture to mock the LLMClient."""
    with patch('core.ai.llm_client.LLMClient') as mock_client:
        # Create a mock client with required methods
        mock = MagicMock()
        mock.analyze_cv = AsyncMock()
        mock.analyze_job = AsyncMock()
        mock_client.return_value = mock
        yield mock

def test_health_check(test_client):
    """Test the health check endpoint."""
    response = test_client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}

@pytest.mark.parametrize("endpoint, data, expected_status", [
    ("/api/analyze/cv", {"text": TEST_CV}, status.HTTP_200_OK),
    ("/api/analyze/job", {"text": TEST_JOB_DESCRIPTION}, status.HTTP_200_OK),
])
@pytest.mark.asyncio
async def test_analyze_endpoints(test_client, endpoint, data, expected_status, mock_llm_client):
    """Test the analysis endpoints."""
    # Setup mock response
    mock_response = {
        "status": "success",
        "data": {
            "skills": ["Python", "FastAPI"],
            "experience": 5,
            "education": [],
            "languages": ["English"]
        },
        "metadata": {}
    }
    
    # Configure the mock based on endpoint
    if "cv" in endpoint:
        mock_llm_client.analyze_cv.return_value = mock_response["data"]
    else:
        mock_llm_client.analyze_job.return_value = mock_response["data"]
    
    # Make the request
    response = test_client.post(
        endpoint,
        json=data,
        headers={"X-API-Key": "test-api-key"}
    )
    
    # Verify the response
    assert response.status_code == expected_status
    result = response.json()
    assert "status" in result
    assert "data" in result
    
    # Verify the correct method was called
    if "cv" in endpoint:
        mock_llm_client.analyze_cv.assert_awaited_once_with(data["text"])
    else:
        mock_llm_client.analyze_job.assert_awaited_once_with(data["text"])
    assert result["status"] == "success"

def test_analyze_without_api_key(test_client):
    """Test that API key is required."""
    response = test_client.post(
        "/api/analyze/cv",
        json={"text": TEST_CV}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    result = response.json()
    assert "detail" in result
    assert "Not authenticated" in result["detail"]

def test_analyze_missing_text(test_client):
    """Test that text parameter is required."""
    response = test_client.post(
        "/api/analyze/cv",
        json={},
        headers={"X-API-Key": "test-api-key"}
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    result = response.json()
    assert "text" in result["detail"][0]["loc"]
    assert any("field required" in str(err.get("msg", "")).lower() 
              for err in result.get("detail", []) if isinstance(err, dict))
