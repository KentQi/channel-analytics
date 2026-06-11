"""
RPA API 路由
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.services import rpa_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rpa", tags=["rpa"])


@router.get("/status")
def get_status(current_user=Depends(get_current_user)):
    """获取调度器状态和统计"""
    return rpa_service.get_scheduler_status()


@router.get("/stats")
def get_stats(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """获取统计信息"""
    return rpa_service.get_stats(db)


@router.get("/modules")
def get_modules(current_user=Depends(get_current_user)):
    """获取支持的采集模块列表"""
    from app.services.rpa_engine import MODULE_CONFIG
    return [{"name": k, **v} for k, v in MODULE_CONFIG.items()]


@router.get("/tasks")
def get_tasks(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """获取所有任务"""
    return rpa_service.get_all_tasks(db)


@router.post("/tasks")
def create_task(data: dict, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """创建任务"""
    if not data.get("name") or not data.get("module_name"):
        raise HTTPException(400, "name 和 module_name 必填")
    if not data.get("schedule_times") or not isinstance(data["schedule_times"], list):
        raise HTTPException(400, "schedule_times 必须是时间点数组，如 ['09:00', '18:00']")
    return rpa_service.create_task(db, data)


@router.get("/tasks/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """获取单个任务"""
    task = rpa_service.get_task(db, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    return task


@router.put("/tasks/{task_id}")
def update_task(task_id: int, data: dict, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """更新任务"""
    task = rpa_service.update_task(db, task_id, data)
    if not task:
        raise HTTPException(404, "任务不存在")
    return task


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """删除任务"""
    rpa_service.delete_task(db, task_id)
    return {"message": "已删除"}


@router.post("/tasks/{task_id}/toggle")
def toggle_task(task_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """启用/禁用任务"""
    task = rpa_service.toggle_task(db, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    return task


@router.post("/tasks/{task_id}/run")
def run_task(task_id: int,
             db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """手动触发单个任务执行"""
    task = rpa_service.get_task(db, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    import threading
    t = threading.Thread(target=rpa_service.execute_task_sync, args=(task_id,), daemon=True)
    t.start()
    return {"message": f"任务 '{task['name']}' 已触发执行", "task_id": task_id}


@router.post("/run-all")
def run_all_tasks(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """临时采集：串行触发所有已启用的任务（Playwright 不能多实例并行），全部完成后统一执行一次 ETL"""
    tasks = rpa_service.get_all_tasks(db)
    enabled = [t for t in tasks if t["enabled"]]
    if not enabled:
        raise HTTPException(400, "没有已启用的任务")
    import threading
    def run_sequentially(task_ids):
        for tid in task_ids:
            try:
                rpa_service.execute_task_sync(tid, skip_etl=True)
            except Exception as e:
                logger.error(f"串行执行任务 #{tid} 异常: {e}")
        # 所有采集任务完成后，统一触发一次 ETL
        try:
            rpa_service.trigger_etl_once()
        except Exception as e:
            logger.error(f"统一 ETL 执行异常: {e}", exc_info=True)
    task_ids = [t["id"] for t in enabled]
    t = threading.Thread(target=run_sequentially, args=(task_ids,), daemon=True)
    t.start()
    return {"message": f"已触发 {len(enabled)} 个任务（串行执行，完成后统一 ETL）", "tasks": [{"id": t["id"], "name": t["name"], "module_name": t["module_name"]} for t in enabled]}


@router.post("/stop")
def stop_tasks(current_user=Depends(get_current_user)):
    """停止所有正在运行的 RPA 采集进程"""
    stopped = rpa_service.stop_all_running()
    if stopped:
        return {"message": f"已停止 {len(stopped)} 个任务", "stopped_task_ids": stopped}
    return {"message": "没有正在运行的任务", "stopped_task_ids": []}


@router.get("/running")
def get_running_tasks(current_user=Depends(get_current_user)):
    """获取正在运行的任务 ID 列表"""
    from app.services.rpa_service import _running_procs
    return {"running_task_ids": list(_running_procs.keys())}


@router.get("/login-config")
def get_login_config(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """获取 RPA 登录配置"""
    from sqlalchemy import text
    configs = {}
    for key in ["rpa_erp_url", "rpa_erp_username", "rpa_erp_password"]:
        row = db.execute(text("SELECT config_value FROM sys_config WHERE config_key=:k"), {"k": key}).fetchone()
        configs[key] = row[0] if row else ""
    # 脱敏：密码只显示前3位
    if configs.get("rpa_erp_password"):
        pw = configs["rpa_erp_password"]
        configs["rpa_erp_password_masked"] = pw[:3] + "***"
    return configs


@router.put("/login-config")
def update_login_config(data: dict, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """更新 RPA 登录配置"""
    from sqlalchemy import text
    for key in ["rpa_erp_url", "rpa_erp_username", "rpa_erp_password"]:
        if key in data and data[key]:
            db.execute(text(
                "UPDATE sys_config SET config_value=:v WHERE config_key=:k"
            ), {"v": data[key], "k": key})
    db.commit()
    return {"message": "登录配置已更新"}


@router.get("/email-config")
def get_email_config(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """获取邮件通知配置"""
    from sqlalchemy import text
    configs = {}
    for key in ["smtp_host", "smtp_port", "smtp_user", "smtp_password", "smtp_default_to"]:
        row = db.execute(text("SELECT config_value FROM sys_config WHERE config_key=:k"), {"k": key}).fetchone()
        configs[key] = row[0] if row else ""
    # 端口转数字
    if configs.get("smtp_port"):
        try:
            configs["smtp_port"] = int(configs["smtp_port"])
        except ValueError:
            configs["smtp_port"] = 465
    else:
        configs["smtp_port"] = 465
    return configs


@router.put("/email-config")
def update_email_config(data: dict, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """更新邮件通知配置"""
    from sqlalchemy import text
    for key in ["smtp_host", "smtp_port", "smtp_user", "smtp_password", "smtp_default_to"]:
        if key in data:
            val = str(data[key]) if data[key] is not None else ""
            existing = db.execute(text("SELECT 1 FROM sys_config WHERE config_key=:k"), {"k": key}).fetchone()
            if existing:
                db.execute(text("UPDATE sys_config SET config_value=:v WHERE config_key=:k"), {"v": val, "k": key})
            else:
                db.execute(text("INSERT INTO sys_config (config_key, config_value) VALUES (:k, :v)"), {"k": key, "v": val})
    db.commit()
    return {"message": "邮件配置已更新"}


@router.get("/logs")
def get_logs(task_id: int = None, limit: int = 50, offset: int = 0,
             db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """获取执行日志"""
    return rpa_service.get_logs(db, task_id=task_id, limit=limit, offset=offset)


@router.post("/test-connection")
def test_connection(data: dict, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """测试ERP system连接"""
    url = data.get("url", "https://erp.example.com")
    username = data.get("username", "")
    password = data.get("password", "")
    if not username or not password:
        raise HTTPException(400, "账号密码必填")
    return rpa_service.test_connection(db, url, username, password)
