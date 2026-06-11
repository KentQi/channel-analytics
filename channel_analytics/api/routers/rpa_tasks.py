"""RpaTasks router — RPA 任务的 CRUD + 触发 + 状态查询。

新仓接口契约(对齐原仓 rpa_tasks 路由的通用部分):
  - GET    /rpa/tasks           — 列出所有任务
  - POST   /rpa/tasks           — 创建任务
  - GET    /rpa/tasks/{id}      — 任务详情
  - POST   /rpa/tasks/{id}/run  — 立即触发(异步)
  - GET    /rpa/logs            — 执行日志(按 task_id 过滤)
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from channel_analytics.api.deps import get_current_user
from channel_analytics.rpa.scheduler import RpaScheduler


router = APIRouter()


# 进程内单例(部署期应替换为 FastAPI Depends 或 lifespan)
_scheduler: RpaScheduler | None = None


def get_scheduler() -> RpaScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = RpaScheduler()
        _scheduler.start()
    return _scheduler


class TaskCreate(BaseModel):
    name: str
    module_names: list[str]
    schedule_cron: str | None = None
    is_active: bool = True
    extra: dict[str, Any] = Field(default_factory=dict)


class TaskOut(BaseModel):
    id: int
    name: str
    module_names: list[str]
    schedule_cron: str | None
    is_active: bool


# 内存存储(部署期应替换为 DB)
_tasks: dict[int, Any] = {}
_next_id = 1


@router.get("/tasks", response_model=list[TaskOut])
async def list_tasks(current_user=Depends(get_current_user)) -> list[TaskOut]:
    from channel_analytics.rpa.scheduler import RpaTask
    return [
        TaskOut(
            id=t.id, name=t.name, module_names=t.module_names,
            schedule_cron=t.schedule_cron, is_active=t.is_active,
        )
        for t in _tasks.values()
    ]


@router.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(req: TaskCreate, current_user=Depends(get_current_user)) -> TaskOut:
    global _next_id
    from channel_analytics.rpa.scheduler import RpaTask
    task = RpaTask(id=_next_id, **req.model_dump())
    _tasks[_next_id] = task
    _next_id += 1
    if task.is_active:
        get_scheduler().register(task, lambda t: None)
    return TaskOut(
        id=task.id, name=task.name, module_names=task.module_names,
        schedule_cron=task.schedule_cron, is_active=task.is_active,
    )


@router.get("/tasks/{task_id}", response_model=TaskOut)
async def get_task(task_id: int, current_user=Depends(get_current_user)) -> TaskOut:
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    t = _tasks[task_id]
    return TaskOut(
        id=t.id, name=t.name, module_names=t.module_names,
        schedule_cron=t.schedule_cron, is_active=t.is_active,
    )


@router.post("/tasks/{task_id}/run", status_code=202)
async def run_task(task_id: int, current_user=Depends(get_current_user)) -> dict[str, str]:
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    # 真实实现: subprocess.Popen(["python", "-m", "channel_analytics.rpa.worker", "--task-id", str(task_id)])
    # 部署方按需实现
    return {"status": "queued", "task_id": str(task_id)}


@router.get("/logs")
async def list_logs(
    task_id: int | None = Query(default=None),
    current_user=Depends(get_current_user),
) -> list[dict[str, Any]]:
    """执行日志(占位:部署期替换为 DB 查询)。"""
    return []


__all__ = ["router"]