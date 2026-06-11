"""
客户生命周期分析 API 测试
验证: RFM修复、cross_tab结构、数据非空
"""
import pytest
from fastapi.testclient import TestClient


class TestCustomerLifecycleAPI:
    """客户生命周期 API 端点测试"""

    def test_endpoint_requires_auth(self, client: TestClient):
        """未登录应返回 401"""
        resp = client.get("/api/advanced/customer-lifecycle")
        assert resp.status_code == 401

    def test_returns_data(self, client: TestClient, auth_headers: dict):
        """应返回非空客户数据"""
        resp = client.get("/api/advanced/customer-lifecycle?months=18", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json().get("data", resp.json())
        assert "customer_data" in data
        assert "metrics" in data
        assert len(data["customer_data"]) > 0, "customer_data should not be empty"

    def test_metrics_structure(self, client: TestClient, auth_headers: dict):
        """metrics 应包含所有阶段计数"""
        resp = client.get("/api/advanced/customer-lifecycle?months=18", headers=auth_headers)
        data = resp.json().get("data", resp.json())
        m = data["metrics"]
        assert "total_customers" in m
        assert "new_count" in m
        assert "growth_count" in m
        assert "mature_count" in m
        assert "decline_count" in m
        assert "churned_count" in m
        assert "avg_clv" in m
        assert m["total_customers"] > 0

    def test_customer_row_fields(self, client: TestClient, auth_headers: dict):
        """每行客户数据应包含必要字段"""
        resp = client.get("/api/advanced/customer-lifecycle?months=18", headers=auth_headers)
        data = resp.json().get("data", resp.json())
        row = data["customer_data"][0]
        required_fields = ["customer", "r", "f", "m", "r_score", "f_score", "m_score", "stage", "clv"]
        for field in required_fields:
            assert field in row, f"Missing field: {field}"

    def test_rfm_scores_valid_range(self, client: TestClient, auth_headers: dict):
        """RFM评分应在 1-3 范围内"""
        resp = client.get("/api/advanced/customer-lifecycle?months=18", headers=auth_headers)
        data = resp.json().get("data", resp.json())
        for row in data["customer_data"]:
            assert 1 <= row["r_score"] <= 3, f"r_score out of range: {row['r_score']}"
            assert 1 <= row["f_score"] <= 3, f"f_score out of range: {row['f_score']}"
            assert 1 <= row["m_score"] <= 3, f"m_score out of range: {row['m_score']}"

    def test_cross_tab_structure(self, client: TestClient, auth_headers: dict):
        """cross_tab 应包含 stages, categories, customer_matrix, amount_matrix"""
        resp = client.get("/api/advanced/customer-lifecycle?months=18", headers=auth_headers)
        data = resp.json().get("data", resp.json())
        ct = data.get("cross_tab", {})
        assert "stages" in ct, "cross_tab should have stages"
        assert "categories" in ct, "cross_tab should have categories"
        assert "customer_matrix" in ct, "cross_tab should have customer_matrix"
        assert "amount_matrix" in ct, "cross_tab should have amount_matrix"
        assert len(ct["stages"]) > 0, "stages should not be empty"
        assert len(ct["categories"]) > 0, "categories should not be empty"

    def test_cross_tab_matrix_dimensions(self, client: TestClient, auth_headers: dict):
        """矩阵维度应与 stages × categories 一致"""
        resp = client.get("/api/advanced/customer-lifecycle?months=18", headers=auth_headers)
        data = resp.json().get("data", resp.json())
        ct = data["cross_tab"]
        n_stages = len(ct["stages"])
        n_cats = len(ct["categories"])
        assert len(ct["customer_matrix"]) == n_stages
        assert len(ct["amount_matrix"]) == n_stages
        for row in ct["customer_matrix"]:
            assert len(row) == n_cats
        for row in ct["amount_matrix"]:
            assert len(row) == n_cats

    def test_cross_tab_categories_include_other(self, client: TestClient, auth_headers: dict):
        """品类列表应包含 '其他' 作为聚合项"""
        resp = client.get("/api/advanced/customer-lifecycle?months=18", headers=auth_headers)
        data = resp.json().get("data", resp.json())
        ct = data["cross_tab"]
        assert "其他" in ct["categories"], "categories should include '其他'"

    def test_different_months(self, client: TestClient, auth_headers: dict):
        """不同追溯周期应返回不同数据量"""
        r6 = client.get("/api/advanced/customer-lifecycle?months=6", headers=auth_headers)
        r18 = client.get("/api/advanced/customer-lifecycle?months=18", headers=auth_headers)
        d6 = r6.json().get("data", r6.json())
        d18 = r18.json().get("data", r18.json())
        # 18个月应包含 >= 6个月的客户数
        assert d18["metrics"]["total_customers"] >= d6["metrics"]["total_customers"]


class TestCustomerLifecycleService:
    """直接测试 service 层（无 HTTP）"""

    def test_service_returns_valid_data(self):
        """service 函数应返回有效数据"""
        from app.database import MainSessionLocal
        from app.services.advanced_analysis_service import get_customer_lifecycle

        db = MainSessionLocal()
        try:
            result = get_customer_lifecycle(db=db, months=18)
            assert "customer_data" in result
            assert "metrics" in result
            assert "cross_tab" in result
            assert len(result["customer_data"]) > 0
            assert result["metrics"]["total_customers"] > 0
            assert len(result["cross_tab"]["stages"]) > 0
        finally:
            db.close()

    def test_rfm_no_value_error(self):
        """RFM分箱不应再抛出 ValueError (修复验证)"""
        from app.database import MainSessionLocal
        from app.services.advanced_analysis_service import get_customer_lifecycle

        db = MainSessionLocal()
        try:
            # 这个调用之前会因为 Bin labels mismatch 而崩溃
            result = get_customer_lifecycle(db=db, months=18)
            assert "error" not in result or result.get("error") is None
        finally:
            db.close()
