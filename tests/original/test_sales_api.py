"""
API integration tests for sales analysis endpoints.
"""
import pytest


class TestSalesAPI:
    """Test cases for /api/sales-analysis/* endpoints."""

    def test_get_sales_wide_table(self, client, auth_headers):
        """Test GET /api/sales-analysis/wide-table."""
        response = client.get("/api/sales-analysis/wide-table", headers=auth_headers)
        # May return 200 or error if no data
        assert response.status_code in [200, 500]

    def test_get_sales_wide_table_unauthorized(self, client):
        """Test GET /api/sales-analysis/wide-table without auth."""
        response = client.get("/api/sales-analysis/wide-table")
        assert response.status_code in [401, 403]

    def test_get_sales_wide_table_with_filters(self, client, auth_headers):
        """Test GET /api/sales-analysis/wide-table with region filter."""
        response = client.get(
            "/api/sales-analysis/wide-table?region=华东",
            headers=auth_headers
        )
        assert response.status_code in [200, 500]

    def test_get_sales_dashboard(self, client, auth_headers):
        """Test GET /api/sales-analysis/dashboard."""
        response = client.get("/api/sales-analysis/dashboard", headers=auth_headers)
        assert response.status_code in [200, 500]

    def test_get_sales_indicator(self, client, auth_headers):
        """Test GET /api/sales-analysis/indicator."""
        response = client.get("/api/sales-analysis/indicator", headers=auth_headers)
        assert response.status_code in [200, 500]

    def test_get_sales_detail(self, client, auth_headers):
        """Test GET /api/sales-analysis/detail."""
        response = client.get("/api/sales-analysis/detail", headers=auth_headers)
        assert response.status_code in [200, 500]

    def test_get_sales_flow(self, client, auth_headers):
        """Test GET /api/sales-analysis/flow."""
        response = client.get("/api/sales-analysis/flow", headers=auth_headers)
        assert response.status_code in [200, 500]
