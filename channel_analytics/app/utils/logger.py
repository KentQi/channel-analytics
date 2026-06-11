"""
JSON Lines logging system.
Outputs logs to the logs/ directory with separate files for audit, business, and error logs.
"""
import json
import threading
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILES = {
    "audit": LOG_DIR / "audit.jsonl",      # 审计日志
    "business": LOG_DIR / "business.jsonl",  # 业务日志
    "error": LOG_DIR / "error.jsonl",        # 错误日志
}

# Thread lock for safe concurrent logging
_log_lock = threading.Lock()

# Ensure all log files exist
for log_file in LOG_FILES.values():
    log_file.touch(exist_ok=True)


def write_log(log_type: str, event: str, details: dict, username: str = None):
    """
    Write a JSON Lines format log entry.

    Args:
        log_type: Type of log (audit, business, error)
        event: Event name
        details: Additional details dictionary
        username: Username performing the action
    """
    log_file = LOG_FILES.get(log_type)
    if log_file is None:
        raise ValueError(f"Unknown log type: {log_type}")

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "username": username,
        "event": event,
        "details": details or {},
    }

    with _log_lock:
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except OSError as e:
            # Log write failure - silently ignore to avoid cascading errors
            # In production, consider logging to stderr or fallback location
            import sys
            print(f"Failed to write log to {log_file}: {e}", file=sys.stderr)


def log_audit(username: str, event: str, details: dict = None):
    """
    Write an audit log entry.

    Args:
        username: Username performing the action
        event: Event name (e.g., login, logout, update_user)
        details: Additional details dictionary
    """
    write_log("audit", event, details or {}, username)


def log_business(username: str, event: str, details: dict = None):
    """
    Write a business log entry.

    Args:
        username: Username performing the action
        event: Event name (e.g., query_data, export_report)
        details: Additional details dictionary
    """
    write_log("business", event, details or {}, username)


def log_error(username: str, event: str, details: dict = None):
    """
    Write an error log entry.

    Args:
        username: Username performing the action (can be None for system errors)
        event: Event/error name
        details: Additional details dictionary
    """
    write_log("error", event, details or {}, username)


# Default logger instance for general logging
logger = {
    "audit": log_audit,
    "business": log_business,
    "error": log_error,
}
