"""
TDD 测试：ETL 定时任务配置 + trigger_source 日志
"""
import pytest
import json
import time as _time
from unittest.mock import patch, MagicMock
from sqlalchemy import text


class TestEtlScheduleConfig:
    """ETL 定时配置 CRUD"""

    def test_get_etl_schedule_config_default(self, client, auth_headers):
        """默认配置：关闭状态，单时间点 08:00，每天"""
        # 先重置为默认值（避免之前测试的干扰）
        from app.database import MainSessionLocal
        from sqlalchemy import text
        db = MainSessionLocal()
        try:
            for key, val in [
                ("etl_schedule_enabled", "false"),
                ("etl_schedule_times", '["08:00"]'),
                ("etl_schedule_days", "daily"),
            ]:
                db.execute(text(
                    "INSERT INTO sys_config (config_key, config_value, updated_at) "
                    "VALUES (:key, :val, NOW()) ON DUPLICATE KEY UPDATE config_value=:val, updated_at=NOW()"
                ), {"key": key, "val": val})
            db.commit()
        finally:
            db.close()

        response = client.get("/api/etl/schedule", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False
        assert data["schedule_times"] == ["08:00"]
        assert data["schedule_days"] == "daily"

    def test_save_etl_schedule_config(self, client, auth_headers):
        """保存配置后读取一致"""
        payload = {
            "enabled": True,
            "schedule_times": ["09:00", "18:00"],
            "schedule_days": "weekdays",
        }
        save_resp = client.put("/api/etl/schedule", json=payload, headers=auth_headers)
        assert save_resp.status_code == 200

        get_resp = client.get("/api/etl/schedule", headers=auth_headers)
        data = get_resp.json()
        assert data["enabled"] is True
        assert data["schedule_times"] == ["09:00", "18:00"]
        assert data["schedule_days"] == "weekdays"

    def test_save_etl_schedule_disabled(self, client, auth_headers):
        """关闭定时后 enabled=false"""
        payload = {"enabled": False, "schedule_times": ["10:00"], "schedule_days": "daily"}
        client.put("/api/etl/schedule", json=payload, headers=auth_headers)

        resp = client.get("/api/etl/schedule", headers=auth_headers)
        assert resp.json()["enabled"] is False

    def test_etl_schedule_unauthorized(self, client):
        """未登录不能访问"""
        resp = client.get("/api/etl/schedule")
        assert resp.status_code in [401, 403]


class TestEtlTriggerSource:
    """trigger_source 写入 rpa_logs"""

    def _insert_etl_log(self, client, auth_headers, trigger_source):
        """通过 API 或直接 DB 插入一条 ETL 日志"""
        from app.database import MainSessionLocal
        db = MainSessionLocal()
        try:
            db.execute(text(
                "INSERT INTO rpa_logs (task_id, task_name, trigger_source, status, started_at) "
                "VALUES (NULL, 'ETL 数据导入', :src, 'success', NOW())"
            ), {"src": trigger_source})
            db.commit()
            log_id = db.execute(text("SELECT LAST_INSERT_ID()")).fetchone()[0]
            return log_id
        finally:
            db.close()

    def test_etl_logs_api_returns_trigger_source(self, client, auth_headers):
        """GET /api/etl/logs 返回 trigger_source 字段"""
        self._insert_etl_log(client, auth_headers, "manual")
        resp = client.get("/api/etl/logs", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        assert "trigger_source" in data[0]

    def test_etl_logs_filter_by_trigger_source(self, client, auth_headers):
        """按 trigger_source 过滤"""
        self._insert_etl_log(client, auth_headers, "manual")
        self._insert_etl_log(client, auth_headers, "scheduled")

        resp = client.get("/api/etl/logs?trigger_source=manual", headers=auth_headers)
        data = resp.json()
        for log in data:
            assert log["trigger_source"] == "manual"

    def test_etl_logs_contain_all_sources(self, client, auth_headers):
        """三种来源的日志都能查到"""
        for src in ["manual", "rpa_auto", "scheduled"]:
            self._insert_etl_log(client, auth_headers, src)

        resp = client.get("/api/etl/logs", headers=auth_headers)
        sources = {log["trigger_source"] for log in resp.json()}
        assert "manual" in sources
        assert "rpa_auto" in sources
        assert "scheduled" in sources


class TestEtlFileScanFallback:
    """文件扫描 fallback 逻辑"""

    def test_scan_uploads_fallback(self, tmp_path):
        """rpa_downloads 缺文件时从 uploads 补充"""
        from pathlib import Path
        import pandas as pd

        # 模拟真实目录结构: backend/rpa_downloads/{date}/
        # scan_etl_files 用 parent.parent 找 etl_data 和 uploads
        rpa_dir = tmp_path / "backend" / "rpa_downloads" / "2026-01-01"
        rpa_dir.mkdir(parents=True)
        df = pd.DataFrame({"col": [1]})
        df.to_excel(str(rpa_dir / "现存量_0101.xlsx"), index=False)

        # uploads 在 rpa_downloads 的祖父目录下
        uploads_dir = tmp_path / "uploads" / "testuser"
        uploads_dir.mkdir(parents=True)
        df2 = pd.DataFrame({"col": [2]})
        df2.to_excel(str(uploads_dir / "采购入库单_0101.xlsx"), index=False)

        # etl_data 同级
        etl_data_dir = tmp_path / "etl_data"
        etl_data_dir.mkdir()

        # 调用扫描逻辑
        from app.services.rpa_service import scan_etl_files
        raw_data = scan_etl_files(str(rpa_dir.parent), "2026-01-01")

        assert "current_stock" in raw_data  # 从 rpa_downloads
        assert "入库单" in raw_data  # 从 uploads 补充
