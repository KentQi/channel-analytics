"""
pytest configuration and fixtures for API integration tests.
"""
import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add project root to path so "from app.xxx" works
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "channel_analytics"))
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def client():
    """Create a test client for the FastAPI application."""
    from app.main import app
    return TestClient(app)


@pytest.fixture(scope="session")
def auth_headers(client):
    """Get authentication headers for an admin user."""
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    if response.status_code == 200:
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    return {}


@pytest.fixture
def test_username():
    """Generate a unique test username for each test."""
    import time
    return f"testuser_{int(time.time())}"
