"""W2补 scheduler 单测。"""
from __future__ import annotations

import time

import pytest

from channel_analytics.scheduler import EtlJobConfig, SchedulerService, run_etl_job


class TestEtlJobConfig:
    def test_defaults(self):
        c = EtlJobConfig(job_id="j1", cron="0 9 * * *")
        assert c.brand_provider_dotted.endswith("ExampleMinimalProvider")
        assert c.business_rules_path == ""
        assert c.engine is None
        assert c.raw_data_loader is None


class TestRunEtlJob:
    def test_runs_with_empty_loader(self):
        """无 raw_data_loader → 空 raw_data,跑通。"""
        c = EtlJobConfig(job_id="j1", cron="0 9 * * *")
        run_etl_job(c)  # 不应抛

    def test_runs_with_loader(self):
        def loader(now):
            return {"stg_purchase_req": []}  # empty list, no DataFrame created
        c = EtlJobConfig(job_id="j2", cron="0 9 * * *", raw_data_loader=loader)
        run_etl_job(c)

    def test_loader_exception_does_not_propagate(self):
        def loader(now):
            raise RuntimeError("loader boom")
        c = EtlJobConfig(job_id="j3", cron="0 9 * * *", raw_data_loader=loader)
        # 异常被吞
        run_etl_job(c)


class TestSchedulerService:
    def test_lifecycle(self):
        s = SchedulerService()
        s.start()
        assert s._scheduler is not None
        s.shutdown()
        assert s._scheduler is None

    def test_double_start_safe(self):
        s = SchedulerService()
        s.start()
        s.start()
        s.shutdown()

    def test_double_shutdown_safe(self):
        s = SchedulerService()
        s.shutdown()  # noop

    def test_schedule_etl_requires_started(self):
        s = SchedulerService()
        with pytest.raises(RuntimeError):
            s.schedule_etl(EtlJobConfig(job_id="j1", cron="0 9 * * *"))

    def test_schedule_and_unschedule(self):
        s = SchedulerService()
        s.start()
        try:
            c = EtlJobConfig(job_id="j1", cron="0 9 * * *")
            s.schedule_etl(c)
            assert "j1" in s.list_etl_jobs()
            s.unschedule_etl("j1")
            assert s.list_etl_jobs() == []
        finally:
            s.shutdown()

    def test_trigger_etl_now_unknown_raises(self):
        s = SchedulerService()
        s.start()
        try:
            with pytest.raises(KeyError):
                s.trigger_etl_now("ghost")
        finally:
            s.shutdown()

    def test_trigger_etl_now_runs_immediately(self):
        s = SchedulerService()
        s.start()
        try:
            s.schedule_etl(EtlJobConfig(job_id="j1", cron="0 9 * * *"))
            s.trigger_etl_now("j1")  # 不应抛
        finally:
            s.shutdown()