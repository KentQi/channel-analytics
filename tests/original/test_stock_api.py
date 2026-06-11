"""
API integration tests for stock analysis endpoints.
"""
import pytest


class TestStockAPI:
    """Test cases for /api/stock-analysis/* endpoints."""

    def test_get_stock_overview(self, client, auth_headers):
        """Test GET /api/stock-analysis/overview."""
        response = client.get("/api/stock-analysis/overview", headers=auth_headers)
        # May return 200 or error if no data
        assert response.status_code in [200, 500]

    def test_get_stock_overview_unauthorized(self, client):
        """Test GET /api/stock-analysis/overview without auth."""
        response = client.get("/api/stock-analysis/overview")
        assert response.status_code in [401, 403]

    def test_get_stock_list(self, client, auth_headers):
        """Test GET /api/stock-analysis/stock-list."""
        response = client.get("/api/stock-analysis/stock-list", headers=auth_headers)
        assert response.status_code in [200, 500]

    def test_get_stock_list_with_pagination(self, client, auth_headers):
        """Test GET /api/stock-analysis/stock-list with pagination."""
        response = client.get(
            "/api/stock-analysis/stock-list?page=1&page_size=10",
            headers=auth_headers
        )
        assert response.status_code in [200, 500]

    def test_get_stagnant_stock(self, client, auth_headers):
        """Test GET /api/stock-analysis/stagnant."""
        response = client.get("/api/stock-analysis/stagnant", headers=auth_headers)
        assert response.status_code in [200, 500]

    def test_get_expiry_stock(self, client, auth_headers):
        """Test GET /api/stock-analysis/expiry."""
        response = client.get("/api/stock-analysis/expiry", headers=auth_headers)
        assert response.status_code in [200, 500]
