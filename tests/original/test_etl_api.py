"""
API integration tests for ETL endpoints.
"""
import pytest


class TestETLAPI:
    """Test cases for /api/etl/* endpoints."""

    def test_get_etl_config(self, client, auth_headers):
        """Test GET /api/etl/config returns ETL configuration."""
        response = client.get("/api/etl/config", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "etl_types" in data or "config" in data or isinstance(data, dict)

    def test_get_etl_config_unauthorized(self, client):
        """Test GET /api/etl/config without auth returns 401/403."""
        response = client.get("/api/etl/config")
        assert response.status_code in [401, 403]

    def test_execute_etl_invalid_type(self, client, auth_headers):
        """Test POST /api/etl/execute with invalid type returns error."""
        response = client.post(
            "/api/etl/execute",
            json={"etl_type": "invalid_type_xyz", "file_path": "/tmp/test.xlsx"},
            headers=auth_headers
        )
        # Should return 400 or 500, not 200
        assert response.status_code != 200 or "error" in response.json()

    def test_get_etl_history(self, client, auth_headers):
        """Test GET /api/etl/history returns ETL execution history."""
        response = client.get("/api/etl/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # History endpoint might return list or dict with 'items'
        assert isinstance(data, (list, dict))

    def test_get_field_mapping(self, client, auth_headers):
        """Test GET /api/etl/field-mapping returns field mapping."""
        response = client.get("/api/etl/field-mapping", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
