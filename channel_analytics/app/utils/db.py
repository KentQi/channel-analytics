"""
Database utility functions.
Provides common database operations with retry logic.
"""
import time
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, SQLAlchemyError

logger = logging.getLogger(__name__)


def execute_with_retry(
    db: Session,
    query: str,
    params: Optional[Dict[str, Any]] = None,
    max_retries: int = 3
) -> Any:
    """
    Execute a database query with retry logic for transient failures.

    Args:
        db: SQLAlchemy session
        query: SQL query string
        params: Query parameters
        max_retries: Maximum retry attempts

    Returns:
        Query result

    Raises:
        OperationalError: If all retries fail
    """
    for attempt in range(max_retries):
        try:
            result = db.execute(text(query), params or {})
            return result
        except OperationalError as e:
            if attempt == max_retries - 1:
                logger.error(f"Database query failed after {max_retries} attempts: {e}")
                raise
            wait_time = 0.5 * (attempt + 1)
            logger.warning(f"Database query failed, retrying in {wait_time}s: {e}")
            time.sleep(wait_time)


def execute_scalar(db: Session, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """
    Execute a query and return a single scalar value.

    Args:
        db: SQLAlchemy session
        query: SQL query string
        params: Query parameters

    Returns:
        Scalar value or None
    """
    result = execute_with_retry(db, query, params)
    row = result.fetchone()
    return row[0] if row else None


def execute_one(db: Session, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Execute a query and return a single row as dict.

    Args:
        db: SQLAlchemy session
        query: SQL query string
        params: Query parameters

    Returns:
        Row as dict or None
    """
    result = execute_with_retry(db, query, params)
    row = result.fetchone()
    if row is None:
        return None
    return dict(row._mapping)


def execute_all(db: Session, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Execute a query and return all rows as list of dicts.

    Args:
        db: SQLAlchemy session
        query: SQL query string
        params: Query parameters

    Returns:
        List of rows as dicts
    """
    result = execute_with_retry(db, query, params)
    rows = result.fetchall()
    return [dict(row._mapping) for row in rows]


def check_connection(db: Session) -> bool:
    """
    Check if database connection is alive.

    Args:
        db: SQLAlchemy session

    Returns:
        True if connection is healthy
    """
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False
