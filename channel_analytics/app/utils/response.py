"""
Response utility functions.
Provides consistent API response formatting.
"""
from typing import Any, Dict, List, Optional


def success_response(
    data: Any = None,
    message: str = "Success",
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a standardized success response.

    Args:
        data: Response data payload
        message: Success message
        meta: Optional metadata (pagination, etc.)

    Returns:
        Formatted success response dict
    """
    response = {
        "success": True,
        "message": message
    }
    if data is not None:
        response["data"] = data
    if meta:
        response["meta"] = meta
    return response


def error_response(
    message: str,
    code: int = 400,
    errors: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Create a standardized error response.

    Args:
        message: Error message
        code: HTTP status code
        errors: Optional list of detailed errors

    Returns:
        Formatted error response dict
    """
    response = {
        "success": False,
        "error": message,
        "code": code
    }
    if errors:
        response["errors"] = errors
    return response


def paginated_response(
    items: List[Any],
    total: int,
    page: int,
    page_size: int
) -> Dict[str, Any]:
    """
    Create a standardized paginated response.

    Args:
        items: List of items for current page
        total: Total number of items
        page: Current page number
        page_size: Items per page

    Returns:
        Formatted paginated response dict
    """
    return {
        "success": True,
        "data": items,
        "meta": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0
        }
    }
