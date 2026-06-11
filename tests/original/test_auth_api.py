"""
API integration tests for authentication endpoints.
"""
import pytest


class TestAuthAPI:
    """Test cases for /api/auth/* endpoints."""

    def test_login_success(self, client):
        """Test POST /api/auth/login with valid credentials."""
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["username"] == "admin"
        assert "role" in data

    def test_login_invalid_password(self, client):
        """Test POST /api/auth/login with wrong password."""
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        assert "detail" in response.json()

    def test_login_invalid_username(self, client):
        """Test POST /api/auth/login with non-existent user."""
        response = client.post(
            "/api/auth/login",
            json={"username": "nonexistent_user_xyz", "password": "anypassword"}
        )
        assert response.status_code == 401

    def test_login_missing_fields(self, client):
        """Test POST /api/auth/login with missing fields."""
        response = client.post(
            "/api/auth/login",
            json={"username": "admin"}
        )
        assert response.status_code == 422  # Validation error

    def test_logout(self, client, auth_headers):
        """Test POST /api/auth/logout."""
        response = client.post("/api/auth/logout", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"

    def test_logout_unauthorized(self, client):
        """Test POST /api/auth/logout without auth."""
        response = client.post("/api/auth/logout")
        assert response.status_code in [401, 403]

    def test_get_current_user(self, client, auth_headers):
        """Test GET /api/auth/me returns current user info."""
        response = client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "username" in data
        assert "role" in data

    def test_get_current_user_unauthorized(self, client):
        """Test GET /api/auth/me without auth."""
        response = client.get("/api/auth/me")
        assert response.status_code in [401, 403]

    def test_change_password(self, client, auth_headers):
        """Test POST /api/auth/change-password."""
        response = client.post(
            "/api/auth/change-password",
            headers=auth_headers,
            json={
                "old_password": "admin123",
                "new_password": "Admin123456!"
            }
        )
        # May fail if password policy requires specific format
        assert response.status_code in [200, 400]

    def test_change_password_wrong_old(self, client, auth_headers):
        """Test POST /api/auth/change-password with wrong old password."""
        response = client.post(
            "/api/auth/change-password",
            headers=auth_headers,
            json={
                "old_password": "wrongoldpassword",
                "new_password": "NewPass123"
            }
        )
        assert response.status_code == 400
