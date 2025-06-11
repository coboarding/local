"""
Tests for the API endpoints.
"""
import json
import pytest

# Test data
TEST_CV = """John Doe
Senior Software Engineer
5+ years of experience in Python and FastAPI"""

TEST_JOB_DESCRIPTION = """Looking for a Senior Software Engineer with:
- 5+ years of Python experience
- Experience with FastAPI
- Knowledge of Docker and Kubernetes"""

def test_health_check(test_client):
    """Test the health check endpoint."""
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.parametrize("endpoint, data, expected_status", [
    ("/api/analyze/cv", {"text": TEST_CV}, 200),
    ("/api/analyze/job", {"text": TEST_JOB_DESCRIPTION}, 200),
])
def test_analyze_endpoints(test_client, endpoint, data, expected_status, mock_ollama):
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
    mock_ollama.return_value.json.return_value = mock_response
    
    response = test_client.post(
        endpoint,
        json=data,
        headers={"X-API-Key": "test-api-key"}
    )
    assert response.status_code == expected_status
    result = response.json()
    assert "status" in result
    assert "data" in result
    assert result["status"] == "success"

def test_analyze_without_api_key(test_client):
    """Test that API key is required."""
    response = test_client.post(
        "/api/analyze/cv",
        json={"text": TEST_CV}
    )
    assert response.status_code == 403
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
    assert response.status_code == 422
    result = response.json()
    assert "detail" in result
    assert any("field required" in str(err.get("msg", "")).lower() 
              for err in result.get("detail", []) if isinstance(err, dict))
