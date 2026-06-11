"""
ETL API router.
Provides endpoints for Excel file upload, ETL execution, and status tracking.
"""
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.dependencies import get_current_user
from app.models.schemas import UserResponse
from app.services.etl_service import run_etl
from app.utils.audit import log_etl
from app.utils.excel_reader import read_excel_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/etl", tags=["etl"])

# ===================== Configuration =====================
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
TASKS_DIR = BASE_DIR / "tasks"
UUID_MAPPING_FILE = TASKS_DIR / "uuid_mapping.json"

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
TASKS_DIR.mkdir(parents=True, exist_ok=True)


# ===================== JSON Storage Helpers =====================
import sys
import tempfile

if sys.platform != "win32":
    import fcntl


def _load_uuid_mapping() -> Dict[str, Dict]:
    """Load UUID to file mapping from JSON (with file lock)."""
    if not UUID_MAPPING_FILE.exists():
        return {}
    with open(UUID_MAPPING_FILE, "r", encoding="utf-8") as f:
        if sys.platform != "win32":
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
        try:
            return json.load(f)
        finally:
            if sys.platform != "win32":
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def _save_uuid_mapping(mapping: Dict[str, Dict]):
    """Save UUID to file mapping to JSON (atomic write with file lock)."""
    # Write to temp file first, then rename (atomic on POSIX)
    dir_ = UUID_MAPPING_FILE.parent
    fd, tmp_path = tempfile.mkstemp(dir=str(dir_), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            if sys.platform != "win32":
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(mapping, f, ensure_ascii=False, indent=2)
                f.flush()
            finally:
                if sys.platform != "win32":
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        os.replace(tmp_path, str(UUID_MAPPING_FILE))
    except Exception:
        os.unlink(tmp_path) if os.path.exists(tmp_path) else None
        raise


def _load_task_status(task_id: str) -> Optional[Dict]:
    """Load task status from JSON file."""
    task_file = TASKS_DIR / "status" / f"{task_id}.json"
    if task_file.exists():
        with open(task_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _save_task_status(task_id: str, task_data: Dict):
    """Save task status to JSON file (atomic write)."""
    status_dir = TASKS_DIR / "status"
    status_dir.mkdir(parents=True, exist_ok=True)
    task_file = status_dir / f"{task_id}.json"
    fd, tmp_path = tempfile.mkstemp(dir=str(status_dir), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(task_data, f, ensure_ascii=False, indent=2)
            f.flush()
        os.replace(tmp_path, str(task_file))
    except Exception:
        os.unlink(tmp_path) if os.path.exists(tmp_path) else None
        raise


def _delete_task_status(task_id: str):
    """Delete task status file."""
    task_file = TASKS_DIR / "status" / f"{task_id}.json"
    if task_file.exists():
        task_file.unlink()


# ===================== Helper Functions =====================
def get_task_status(task_id: str) -> Optional[Dict]:
    """Get task status by ID from JSON storage."""
    return _load_task_status(task_id)


def _detect_file_type(filename: str) -> Optional[str]:
    """
    根据文件名自动识别文件类型
    支持的文件类型：
    - 请购单 / 请购单.xlsx
    - 采购单 / 采购单.xlsx
    - 入库单 / 采购入库 / 入库.xlsx
    - 销售出库单 / 销售出库.xlsx
    - 现存量 / 库存查询
    """
    name = filename.lower()
    if '请购' in name:
        return '请购单'
    elif '采购单' in name and '入库' not in name:
        return '采购单'
    elif '入库' in name or '采购入库' in name:
        return '入库单'
    elif '销售出库' in name:
        return '销售出库单'
    elif '现存量' in name or '库存查询' in name:
        return '现存量'
    return None


def update_task_status(task_id: str, status: str, **kwargs):
    """Update task status in JSON storage."""
    task = _load_task_status(task_id)
    if task:
        task.update({
            "status": status,
            "updated_at": datetime.now().isoformat(),
            **kwargs
        })
        _save_task_status(task_id, task)


def _execute_etl_task(task_id: str, file_paths: list):
    """
    Execute ETL task in background.

    Args:
        task_id: Unique task identifier
        file_paths: List of file paths to process
    """
    from app.database import MainSessionLocal

    db = MainSessionLocal()
    try:
        update_task_status(task_id, "running", message="Processing files...")

        # Read Excel files and map to expected sheet names
        raw_data = {}
        # Expected sheet name mapping
        sheet_name_mapping = {
            "请购单": ["请购单", "请购单列表", "采购申请"],
            "采购单": ["采购单", "采购单列表", "采购订单"],
            "入库单": ["入库单", "采购入库单列表", "采购入库", "入库"],
            "销售出库单": ["销售出库单", "销售出库单列表", "销售出库"],
            "current_stock": ["现存量", "现存量查询", "库存查询", "存量分析头", "current_stock"],
        }

        for file_path in file_paths:
            file_path = Path(file_path)
            sheet_data = read_excel_file(str(file_path))

            # Match this file to one expected_name
            matched = False
            for expected_name, possible_names in sheet_name_mapping.items():
                if expected_name in raw_data:
                    continue  # Already matched
                for actual_sheet in sheet_data.keys():
                    if actual_sheet in possible_names or any(pn in actual_sheet for pn in possible_names):
                        raw_data[expected_name] = sheet_data[actual_sheet]
                        matched = True
                        break
                if matched:
                    break

        update_task_status(task_id, "running", message="Running ETL...")

        # Execute ETL (passes db session for DB writes)
        import time
        t0 = time.time()
        result = run_etl(raw_data, db)
        duration = time.time() - t0

        update_task_status(
            task_id,
            "completed",
            message="ETL completed successfully",
            result=result
        )
        log_etl(task_id, "completed", duration)
        logger.info(f"ETL task {task_id} completed successfully")

    except Exception as e:
        logger.error(f"ETL task {task_id} failed: {e}")
        log_etl(task_id, "failed")
        update_task_status(task_id, "failed", message=str(e), error=str(e))
    finally:
        db.close()


# ===================== API Endpoints =====================
@router.post("/upload", response_model=Dict)
async def upload_file(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Upload an Excel file for ETL processing.

    Args:
        file: Excel file to upload
        current_user: Authenticated user

    Returns:
        Upload result with file ID and path
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are allowed")

    # Generate unique file ID
    file_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create user-specific upload directory
    user_dir = UPLOAD_DIR / current_user.username
    user_dir.mkdir(parents=True, exist_ok=True)

    # Save file with secure naming
    filename = f"{timestamp}_{file_id}_{file.filename}"
    file_path = user_dir / filename

    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        # Store UUID mapping for secure file lookup
        mapping = _load_uuid_mapping()
        mapping[file_id] = {
            "file_path": str(file_path),
            "original_filename": file.filename,
            "uploaded_by": current_user.username,
            "uploaded_at": datetime.now().isoformat(),
            "size": len(contents),
            # 根据文件名自动识别文件类型
            "file_type": _detect_file_type(file.filename),
        }
        _save_uuid_mapping(mapping)

        logger.info(f"User {current_user.username} uploaded file: {filename} (ID: {file_id})")

        return {
            "file_id": file_id,
            "filename": file.filename,
            "saved_path": str(file_path),
            "size": len(contents),
            "uploaded_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"File upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@router.post("/execute", response_model=Dict)
async def execute_etl(
    background_tasks: BackgroundTasks,
    file_ids: list[str],
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Execute ETL process on uploaded files (background task).

    Args:
        background_tasks: FastAPI background tasks
        file_ids: List of file IDs to process
        current_user: Authenticated user

    Returns:
        Task ID for tracking execution status
    """
    if not file_ids:
        raise HTTPException(status_code=400, detail="No file IDs provided")

    # Secure file lookup with ownership verification
    mapping = _load_uuid_mapping()
    file_paths = []
    for file_id in file_ids:
        if file_id not in mapping:
            logger.warning(f"File ID not found: {file_id}")
            continue

        file_info = mapping[file_id]

        # Verify ownership
        if file_info.get("uploaded_by") != current_user.username:
            logger.warning(f"User {current_user.username} attempted to access file owned by {file_info.get('uploaded_by')}")
            raise HTTPException(status_code=403, detail=f"Access denied to file: {file_id}")

        file_path = Path(file_info["file_path"])
        if not file_path.exists():
            logger.warning(f"File not found on disk: {file_path}")
            continue

        file_paths.append(file_path)

    if not file_paths:
        raise HTTPException(status_code=404, detail="No valid files found for the given IDs")

    # Create task with JSON storage
    task_id = str(uuid.uuid4())
    task_data = {
        "task_id": task_id,
        "file_ids": file_ids,
        "file_count": len(file_paths),
        "status": "pending",
        "created_by": current_user.username,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "message": "Task queued",
    }
    _save_task_status(task_id, task_data)

    # Execute in background
    background_tasks.add_task(_execute_etl_task, task_id, file_paths)

    logger.info(f"User {current_user.username} started ETL task: {task_id}")

    return {
        "task_id": task_id,
        "status": "pending",
        "message": "ETL task queued for execution",
        "file_count": len(file_paths),
    }


@router.get("/status/{task_id}", response_model=Dict)
async def get_etl_status(
    task_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Get ETL task status.

    Args:
        task_id: Task identifier
        current_user: Authenticated user

    Returns:
        Task status and details
    """
    task = get_task_status(task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    # Verify ownership
    if task.get("created_by") != current_user.username:
        raise HTTPException(status_code=403, detail="Access denied to this task")

    # Don't expose sensitive info
    result = {
        "task_id": task["task_id"],
        "status": task["status"],
        "message": task.get("message"),
        "file_count": task.get("file_count"),
        "created_at": task.get("created_at"),
        "updated_at": task.get("updated_at"),
    }

    # Include summary if completed
    if task["status"] == "completed" and "result" in task:
        result["summary"] = task["result"].get("summary", {})

    # Include error if failed
    if task["status"] == "failed":
        result["error"] = task.get("error")

    return result


@router.get("/files", response_model=Dict)
async def list_uploaded_files(
    current_user: UserResponse = Depends(get_current_user),
):
    """
    List all uploaded files for the current user.

    Args:
        current_user: Authenticated user

    Returns:
        List of uploaded files
    """
    # Load UUID mapping and filter by user
    mapping = _load_uuid_mapping()
    files = []

    for file_id, file_info in mapping.items():
        # Only list files owned by current user
        if file_info.get("uploaded_by") != current_user.username:
            continue

        file_path = Path(file_info["file_path"])
        if file_path.exists():
            stat = file_path.stat()
            files.append({
                "file_id": file_id,
                "filename": file_info.get("original_filename"),
                "size": file_info.get("size", stat.st_size),
                "uploaded_at": file_info.get("uploaded_at"),
            })
        else:
            # File was deleted externally, mark as orphaned
            logger.warning(f"Orphaned file entry: {file_id} at {file_info['file_path']}")

    # Sort by upload time descending
    files.sort(key=lambda x: x["uploaded_at"] or "", reverse=True)

    return {
        "files": files,
        "total": len(files),
    }


@router.delete("/files/{file_id}", response_model=Dict)
async def delete_uploaded_file(
    file_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Delete an uploaded file.

    Args:
        file_id: File identifier
        current_user: Authenticated user

    Returns:
        Deletion result
    """
    # Load UUID mapping
    mapping = _load_uuid_mapping()

    if file_id not in mapping:
        raise HTTPException(status_code=404, detail="File not found")

    file_info = mapping[file_id]

    # Verify ownership
    if file_info.get("uploaded_by") != current_user.username:
        logger.warning(f"User {current_user.username} attempted to delete file owned by {file_info.get('uploaded_by')}")
        raise HTTPException(status_code=403, detail="Access denied to this file")

    file_path = Path(file_info["file_path"])

    try:
        # Delete physical file
        if file_path.exists():
            file_path.unlink()

        # Remove from UUID mapping
        del mapping[file_id]
        _save_uuid_mapping(mapping)

        logger.info(f"User {current_user.username} deleted file: {file_id}")

        return {"message": "File deleted successfully", "file_id": file_id}

    except Exception as e:
        logger.error(f"File deletion failed: {e}")
        raise HTTPException(status_code=500, detail=f"File deletion failed: {str(e)}")


@router.post("/preview", response_model=Dict)
async def preview_file(
    file_id: str,
    sheet_name: Optional[str] = None,
    max_rows: int = 10,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Preview an uploaded Excel file.

    Args:
        file_id: File identifier
        sheet_name: Optional sheet name to preview
        max_rows: Maximum rows to return (default 10)
        current_user: Authenticated user

    Returns:
        Preview data
    """
    # Secure file lookup with ownership verification
    mapping = _load_uuid_mapping()

    if file_id not in mapping:
        raise HTTPException(status_code=404, detail="File not found")

    file_info = mapping[file_id]

    # Verify ownership
    if file_info.get("uploaded_by") != current_user.username:
        logger.warning(f"User {current_user.username} attempted to preview file owned by {file_info.get('uploaded_by')}")
        raise HTTPException(status_code=403, detail="Access denied to this file")

    file_path = Path(file_info["file_path"])

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    try:
        sheet_data = read_excel_file(str(file_path))

        if sheet_name:
            if sheet_name not in sheet_data:
                raise HTTPException(status_code=404, detail=f"Sheet '{sheet_name}' not found")
            df = sheet_data[sheet_name]
        else:
            # Return first sheet
            sheet_name = list(sheet_data.keys())[0]
            df = sheet_data[sheet_name]

        # Limit rows
        df_preview = df.head(max_rows)

        return {
            "sheet_name": sheet_name,
            "sheets": list(sheet_data.keys()),
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "preview": {
                "columns": df_preview.columns.tolist(),
                "data": df_preview.values.tolist(),
            }
        }

    except Exception as e:
        logger.error(f"File preview failed: {e}")
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


# STG 表名列表
STG_TABLES = [
    ("stg_purchase_req", "请购单"),
    ("stg_purchase_order", "采购单"),
    ("stg_stock_in", "入库单"),
    ("stg_sales_out", "销售出库单"),
    ("stg_stock_current", "现存量"),
]


@router.get("/db-status", response_model=Dict)
async def get_db_status(
    current_user: UserResponse = Depends(get_current_user),
):
    """Check database connection and return STG table info."""
    from app.database import main_engine
    status = {"connected": False, "table_count": 0, "stg_tables": []}
    try:
        with main_engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE()"))
            status["table_count"] = result.scalar() or 0
            status["connected"] = True
            # Check which STG tables exist and have data
            for table_name, label in STG_TABLES:
                try:
                    cnt = conn.execute(text(f"SELECT COUNT(*) FROM `{table_name}`")).scalar() or 0
                    status["stg_tables"].append({"name": table_name, "label": label, "rows": cnt})
                except Exception:
                    status["stg_tables"].append({"name": table_name, "label": label, "rows": 0})
    except Exception as e:
        logger.error(f"DB status check failed: {e}")
        status["error"] = str(e)
    return status


@router.get("/stg-preview/{table_key}", response_model=Dict)
async def preview_stg_table(
    table_key: str,
    max_rows: int = 100,
    current_user: UserResponse = Depends(get_current_user),
):
    """Preview data from a STG table by key."""
    from app.services.field_mapping import (
        REVERSE_STG_PURCHASE_REQ,
        REVERSE_STG_PURCHASE_ORDER,
        REVERSE_STG_STOCK_IN,
        REVERSE_STG_SALES_OUT,
        REVERSE_STG_STOCK_CURRENT,
    )

    # 表名到反向映射的对应关系
    TABLE_REVERSE_MAPS = {
        "stg_purchase_req": REVERSE_STG_PURCHASE_REQ,
        "stg_purchase_order": REVERSE_STG_PURCHASE_ORDER,
        "stg_stock_in": REVERSE_STG_STOCK_IN,
        "stg_sales_out": REVERSE_STG_SALES_OUT,
        "stg_stock_current": REVERSE_STG_STOCK_CURRENT,
    }

    key_to_table = {item[0]: item[0] for item in STG_TABLES}
    key_to_table.update({item[1]: item[0] for item in STG_TABLES})
    table_name = key_to_table.get(table_key)
    if not table_name:
        raise HTTPException(status_code=404, detail=f"Unknown STG table: {table_key}")
    try:
        from app.database import main_engine
        import pandas as pd
        from datetime import date, datetime
        df = pd.read_sql(f"SELECT * FROM `{table_name}` LIMIT {max_rows}", main_engine)
        total_rows = main_engine.connect().execute(text(f"SELECT COUNT(*) FROM `{table_name}`")).scalar() or 0

        # 获取该表的反向映射（英→中）
        reverse_map = TABLE_REVERSE_MAPS.get(table_name, {})

        # 将列名转换为中文
        display_columns = [reverse_map.get(col, col) for col in df.columns]

        # Convert all values to JSON-serializable types
        def convert_value(v):
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return ""
            if isinstance(v, (datetime, date)):
                return v.isoformat() if hasattr(v, 'isoformat') else str(v)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                if isinstance(v, float) and v != v:  # NaN check
                    return ""
                return v
            return str(v)

        data = [[convert_value(v) for v in row] for row in df.fillna("").values.tolist()]

        return {
            "table_name": table_name,
            "total_rows": total_rows,
            "total_columns": len(display_columns),
            "columns": display_columns,
            "data": data,
        }
    except Exception as e:
        logger.error(f"STG preview failed for {table_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")
