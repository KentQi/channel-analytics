"""
审计日志工具 — 记录关键操作到 logs/audit.log, logs/business.log, logs/error.log
"""
import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# ── 写入日志 ──────────────────────────────────────────────

_audit_logger = logging.getLogger("audit")
_audit_logger.setLevel(logging.INFO)

_handler = logging.FileHandler(os.path.join(LOG_DIR, "audit.log"), encoding="utf-8")
_handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
_audit_logger.addHandler(_handler)

_business_logger = logging.getLogger("business")
_business_logger.setLevel(logging.INFO)
_biz_handler = logging.FileHandler(os.path.join(LOG_DIR, "business.log"), encoding="utf-8")
_biz_handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
_business_logger.addHandler(_biz_handler)

_error_logger = logging.getLogger("error")
_error_logger.setLevel(logging.INFO)
_err_handler = logging.FileHandler(os.path.join(LOG_DIR, "error.log"), encoding="utf-8")
_err_handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
_error_logger.addHandler(_err_handler)


def _write_jsonl(logger: logging.Logger, entry: dict):
    """Write a JSON line to the given logger."""
    logger.info(json.dumps(entry, ensure_ascii=False))


def log_login(username: str, success: bool, ip: str = ""):
    event = "AUTH_LOGIN" if success else "AUTH_LOGIN_FAIL"
    _write_jsonl(_audit_logger, {
        "event": event,
        "level": "INFO" if success else "WARN",
        "user": username,
        "role": "",
        "ip": ip,
        "message": f"{'登录成功' if success else '登录失败'}: {username}"
    })


def log_logout(username: str, ip: str = ""):
    _write_jsonl(_audit_logger, {
        "event": "AUTH_LOGOUT",
        "level": "INFO",
        "user": username,
        "role": "",
        "ip": ip,
        "message": f"退出登录: {username}"
    })


def log_data_import(username: str, table: str, success_count: int, error_count: int):
    _write_jsonl(_business_logger, {
        "event": "DATA_IMPORT",
        "level": "ERROR" if error_count > 0 else "INFO",
        "user": username,
        "role": "",
        "ip": "",
        "message": f"数据导入: {table} 成功={success_count} 失败={error_count}"
    })


def log_etl(username: str, status: str, duration_sec: float = 0):
    event_map = {"start": "ETL_START", "done": "ETL_DONE", "fail": "ETL_FAIL"}
    level_map = {"start": "INFO", "done": "INFO", "fail": "ERROR"}
    event = event_map.get(status, "ETL_START")
    level = level_map.get(status, "INFO")
    _write_jsonl(_business_logger, {
        "event": event,
        "level": level,
        "user": username,
        "role": "",
        "ip": "",
        "message": f"ETL {status}: 耗时 {duration_sec:.1f}s"
    })


def log_permission_change(username: str, target_role: str, action: str):
    _write_jsonl(_audit_logger, {
        "event": "PERM_CHANGE",
        "level": "WARN",
        "user": username,
        "role": "",
        "ip": "",
        "message": f"权限变更: {action} {target_role}"
    })


def log_password_change(username: str):
    _write_jsonl(_audit_logger, {
        "event": "PWD_CHANGE",
        "level": "INFO",
        "user": username,
        "role": "",
        "ip": "",
        "message": f"密码修改: {username}"
    })


def log_page_crash(username: str, page: str, error_msg: str):
    _write_jsonl(_error_logger, {
        "event": "PAGE_CRASH",
        "level": "ERROR",
        "user": username,
        "role": "",
        "ip": "",
        "message": f"页面崩溃: {page} - {error_msg}"
    })


# ── 读取日志 ──────────────────────────────────────────────

LOG_FILES = {
    "audit": os.path.join(LOG_DIR, "audit.log"),
    "business": os.path.join(LOG_DIR, "business.log"),
    "error": os.path.join(LOG_DIR, "error.log"),
}


def read_logs(
    log_type: str,
    type_filter: str = "",
    level_filter: str = "",
    user_filter: str = "",
    keyword: str = "",
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """
    Read logs from JSONL file with optional filters.

    Each line in the log file is either:
      - JSON object (new format)
      - "timestamp | message" plain text (legacy format)

    Returns most recent entries first (up to `limit`).
    """
    filepath = LOG_FILES.get(log_type)
    if not filepath or not os.path.exists(filepath):
        return []

    entries: List[Dict[str, Any]] = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = _parse_log_line(line)
            if entry is None:
                continue

            # Apply filters
            if type_filter and entry.get("event", "") != type_filter:
                continue
            if level_filter and entry.get("level", "") != level_filter:
                continue
            if user_filter and user_filter.lower() not in entry.get("user", "").lower():
                continue
            if keyword and keyword.lower() not in entry.get("message", "").lower():
                continue

            entries.append(entry)

    # Return most recent first
    entries.reverse()
    return entries[:limit]


def _parse_log_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse a single log line into a dict."""
    # Try JSON format first
    try:
        obj = json.loads(line)
        if isinstance(obj, dict):
            return obj
    except (json.JSONDecodeError, ValueError):
        pass

    # Legacy format: "timestamp | message"
    parts = line.split(" | ", 1)
    if len(parts) == 2:
        return {
            "timestamp": parts[0],
            "level": "INFO",
            "event": "",
            "user": "",
            "role": "",
            "ip": "",
            "message": parts[1],
        }
    return {
        "timestamp": "",
        "level": "INFO",
        "event": "",
        "user": "",
        "role": "",
        "ip": "",
        "message": line,
    }
