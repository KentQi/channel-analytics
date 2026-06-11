"""
API integration tests for permissions endpoints.
"""
import pytest


class TestPermissionsAPI:
    """Test cases for /api/permissions/* endpoints."""

    def test_list_roles(self, client, auth_headers):
        """Test GET /api/permissions/roles returns role list."""
        response = client.get("/api/permissions/roles", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_roles_unauthorized(self, client):
        """Test GET /api/permissions/roles without auth returns 401/403."""
        response = client.get("/api/permissions/roles")
        assert response.status_code in [401, 403]

    def test_get_role(self, client, auth_headers):
        """Test GET /api/permissions/roles/{role} returns role details."""
        response = client.get("/api/permissions/roles/admin", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"
        assert "permissions" in data

    def test_get_role_not_found(self, client, auth_headers):
        """Test GET /api/permissions/roles/{nonexistent} returns 404."""
        response = client.get("/api/permissions/roles/nonexistent_role_xyz", headers=auth_headers)
        assert response.status_code == 404

    def test_list_users(self, client, auth_headers):
        """Test GET /api/permissions/users returns user list."""
        response = client.get("/api/permissions/users", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    def test_list_users_with_pagination(self, client, auth_headers):
        """Test GET /api/permissions/users with pagination."""
        response = client.get("/api/permissions/users?page=1&page_size=10", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10

    def test_create_user(self, client, auth_headers, test_username):
        """Test POST /api/permissions/users creates a new user."""
        response = client.post(
            f"/api/permissions/users?username={test_username}&display_name=Test User&password=Test123&role=admin",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "用户创建成功"
        assert "user_id" in data

    def test_create_user_duplicate(self, client, auth_headers, test_username):
        """Test POST /api/permissions/users with duplicate username fails."""
        # Create user first
        client.post(
            f"/api/permissions/users?username={test_username}&display_name=Test&password=Test123&role=admin",
            headers=auth_headers
        )
        # Try to create again
        response = client.post(
            f"/api/permissions/users?username={test_username}&display_name=Test2&password=Test123&role=admin",
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "已存在" in response.json()["detail"]

    def test_update_role_permissions(self, client, auth_headers):
        """Test PUT /api/permissions/roles/{role} updates permissions."""
        permissions = {
            "modules": ["etl", "sales"],
            "sales_tabs": ["dashboard"],
            "regions": ["华东", "华北"]
        }
        response = client.put(
            "/api/permissions/roles/admin",
            json=permissions,
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["message"] == "权限更新成功"

    def test_update_role_not_found(self, client, auth_headers):
        """Test PUT /api/permissions/roles/{nonexistent} returns 404."""
        permissions = {"modules": ["etl"]}
        response = client.put(
            "/api/permissions/roles/nonexistent_role_xyz",
            json=permissions,
            headers=auth_headers
        )
        assert response.status_code == 404

    def test_update_role_empty_permissions(self, client, auth_headers):
        """Test PUT /api/permissions/roles with empty permissions returns 400."""
        permissions = {}
        response = client.put(
            "/api/permissions/roles/admin",
            json=permissions,
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "权限不能为空" in response.json()["detail"]

    def test_get_available_regions(self, client, auth_headers):
        """Test GET /api/permissions/regions returns region list."""
        response = client.get("/api/permissions/regions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "regions" in data
        assert isinstance(data["regions"], list)

    def test_get_available_roles(self, client, auth_headers):
        """Test GET /api/permissions/available-roles returns role list."""
        response = client.get("/api/permissions/available-roles", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "roles" in data
        assert isinstance(data["roles"], list)
