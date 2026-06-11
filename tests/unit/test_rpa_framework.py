"""W2补 RPA 框架单测。"""
from __future__ import annotations

from pathlib import Path

import pytest

from channel_analytics.rpa.adapters.example_minimal import ExampleMinimalAdapter
from channel_analytics.rpa.base import ErpAdapter
from channel_analytics.rpa.exceptions import (
    ExportError,
    LoginError,
    NavigateError,
    RpaError,
    SearchError,
)
from channel_analytics.rpa.excel_compat import apply_openpyxl_compat, safe_read_excel
from channel_analytics.rpa.runner import ModuleResult, RpaRunner, RpaRunnerConfig
from channel_analytics.rpa.scheduler import RpaLog, RpaScheduler, RpaTask


# ---------------------------------------------------------------------------
# ErpAdapter
# ---------------------------------------------------------------------------

class TestErpAdapter:
    def test_example_minimal_raises_on_all_hooks(self):
        adapter = ExampleMinimalAdapter()
        with pytest.raises(NotImplementedError):
            import asyncio
            asyncio.run(adapter.login(None, "", "", ""))
        with pytest.raises(NotImplementedError):
            asyncio.run(adapter.navigate_to_module(None, ""))
        with pytest.raises(NotImplementedError):
            asyncio.run(adapter.search(None))
        with pytest.raises(NotImplementedError):
            asyncio.run(adapter.export(None, Path(".")))

    def test_abstract_class_cannot_be_instantiated_directly(self):
        from channel_analytics.rpa.base import ErpAdapter
        with pytest.raises(TypeError):
            ErpAdapter()  # ABC


class TestExceptions:
    def test_login_error_inherits_rpa_error(self):
        assert issubclass(LoginError, RpaError)

    def test_navigate_error_inherits_rpa_error(self):
        assert issubclass(NavigateError, RpaError)

    def test_export_error_inherits_rpa_error(self):
        assert issubclass(ExportError, RpaError)

    def test_search_error_inherits_rpa_error(self):
        assert issubclass(SearchError, RpaError)


class TestExcelCompat:
    def test_apply_openpyxl_compat_idempotent(self):
        """重复调用不应破坏(无副作用)。"""
        apply_openpyxl_compat()
        apply_openpyxl_compat()
        # 没异常就 OK

    def test_safe_read_excel_real_file(self, tmp_path):
        """读真实 .xlsx 不抛异常。"""
        import pandas as pd
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        path = tmp_path / "test.xlsx"
        df.to_excel(path, index=False)
        result = safe_read_excel(path)
        assert result["a"].tolist() == [1, 2]


# ---------------------------------------------------------------------------
# RpaRunner — mock adapter 测试(不需要真的 Playwright)
# ---------------------------------------------------------------------------

class _FakePage:
    pass


class _FakeAdapter(ErpAdapter):
    """测试用 adapter — 记录调用,按 config 行为。"""
    def __init__(self, fail_on: str | None = None) -> None:
        self.calls: list[str] = []
        self._fail_on = fail_on

    async def login(self, page, url, username, password):
        self.calls.append(f"login:{url}")
        if self._fail_on == "login":
            raise LoginError("bad password")

    async def navigate_to_module(self, page, module):
        self.calls.append(f"nav:{module}")
        if self._fail_on == "nav":
            raise NavigateError(f"no module {module}")

    async def set_date_filter(self, page, start_date, end_date):
        self.calls.append(f"date:{start_date}..{end_date}")

    async def search(self, page):
        self.calls.append("search")
        if self._fail_on == "search":
            raise SearchError("no results")

    async def export(self, page, download_dir):
        self.calls.append("export")
        if self._fail_on == "export":
            raise ExportError("download timeout")
        return "/tmp/output.xlsx"


class TestRpaRunnerConfig:
    def test_default_values(self):
        c = RpaRunnerConfig()
        assert c.headless is True
        assert c.slow_mo_ms == 300
        assert c.timeout_ms == 30_000
        assert c.retries == 1


class TestModuleResult:
    def test_success_result(self):
        r = ModuleResult(module="m1", success=True, file_path="/tmp/x.xlsx")
        assert r.success
        assert r.error is None

    def test_failure_result(self):
        r = ModuleResult(module="m1", success=False, error="login: bad")
        assert not r.success
        assert "login" in r.error


# ---------------------------------------------------------------------------
# RpaScheduler
# ---------------------------------------------------------------------------

class TestRpaScheduler:
    def test_lifecycle(self):
        s = RpaScheduler()
        s.start()
        assert s._scheduler is not None
        s.shutdown()
        assert s._scheduler is None

    def test_double_start_is_safe(self):
        s = RpaScheduler()
        s.start()
        s.start()  # noop
        s.shutdown()

    def test_double_shutdown_is_safe(self):
        s = RpaScheduler()
        s.shutdown()  # noop when not started

    def test_register_requires_started(self):
        s = RpaScheduler()
        with pytest.raises(RuntimeError):
            s.register(RpaTask(id=1, name="t", module_names=["m1"]), lambda t: None)

    def test_register_and_list(self):
        s = RpaScheduler()
        s.start()
        try:
            t = RpaTask(
                id=1, name="task1",
                module_names=["m1", "m2"],
                schedule_cron=None,  # 无 cron = 不实际调度,只注册到内存
            )
            s.register(t, lambda task: None)
            assert len(s.list_tasks()) == 1
            assert s.list_tasks()[0].name == "task1"
            s.unregister(1)
            assert s.list_tasks() == []
        finally:
            s.shutdown()

    def test_register_with_cron(self):
        s = RpaScheduler()
        s.start()
        try:
            t = RpaTask(
                id=1, name="task1", module_names=["m1"],
                schedule_cron="0 9 * * *", is_active=True,
            )
            s.register(t, lambda task: None)
            assert s._scheduler.get_job("rpa_task_1") is not None
        finally:
            s.shutdown()

    def test_register_inactive_task_not_scheduled(self):
        s = RpaScheduler()
        s.start()
        try:
            t = RpaTask(
                id=1, name="task1", module_names=["m1"],
                schedule_cron="0 9 * * *", is_active=False,
            )
            s.register(t, lambda task: None)
            assert s._scheduler.get_job("rpa_task_1") is None
        finally:
            s.shutdown()

    def test_mark_done_success(self):
        s = RpaScheduler()
        log = RpaLog(task_id=1, task_name="t", started_at=__import__("datetime").datetime.utcnow())
        s.mark_start(RpaTask(id=1, name="t", module_names=[]))
        results = [ModuleResult(module="m1", success=True, file_path="/tmp/x.xlsx")]
        s.mark_done(log, results)
        assert log.status == "success"
        assert log.finished_at is not None

    def test_mark_done_partial_failure(self):
        s = RpaScheduler()
        log = RpaLog(task_id=1, task_name="t", started_at=__import__("datetime").datetime.utcnow())
        results = [
            ModuleResult(module="m1", success=True, file_path="/tmp/a.xlsx"),
            ModuleResult(module="m2", success=False, error="login: bad"),
        ]
        s.mark_done(log, results)
        assert log.status == "failed"
        assert "login" in (log.error_msg or "")

    def test_cleanup_stale_running_memory_only(self):
        s = RpaScheduler()
        from datetime import datetime
        s._running[1] = RpaLog(task_id=1, task_name="t", started_at=datetime.utcnow())
        s._running[2] = RpaLog(task_id=2, task_name="t2", started_at=datetime.utcnow())
        cleaned = s.cleanup_stale_running(storage=None)
        assert cleaned == 2
        assert s._running == {}


# ---------------------------------------------------------------------------
# Worker CLI 解析
# ---------------------------------------------------------------------------

class TestWorkerCLI:
    def test_parse_required_args(self):
        from channel_analytics.rpa.worker import _parse_args
        args = _parse_args(["--task-id", "42"])
        assert args.task_id == 42
        assert args.skip_etl is False
        assert args.adapter == ""  # 来自环境变量

    def test_parse_all_args(self):
        from channel_analytics.rpa.worker import _parse_args
        args = _parse_args([
            "--task-id", "1", "--module", "m1",
            "--skip-etl", "--adapter", "pkg.mod:Cls",
            "--log-file", "/tmp/worker.log",
        ])
        assert args.module == "m1"
        assert args.skip_etl is True
        assert args.adapter == "pkg.mod:Cls"
        assert args.log_file == "/tmp/worker.log"