"""
Test configuration and fixtures for the coBoarding test suite.
"""
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

# Add the project root to the Python path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock environment variables for testing
os.environ.update({
    "REDIS_URL": "redis://test-redis:6379/0",
    "OLLAMA_BASE_URL": "http://test-ollama:11434",
    "SECRET_KEY": "test-secret-key",
    "API_KEY": "test-api-key"
})

@pytest.fixture(scope="module")
def test_client():
    """Create a test client for the FastAPI application."""
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
