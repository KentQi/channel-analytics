"""
Custom Report API Router
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.custom_report_schemas import (
    ReportPreviewRequest,
    ReportExecuteRequest,
    ReportExportRequest,
    CustomReportCreate,
    CustomReportUpdate,
    CustomReportResponse,
    CustomReportShare,
    TableInfo,
    FieldInfo,
)
from app.models.schemas import UserResponse
from app.services import custom_report_service

router = APIRouter(prefix="/reports", tags=["自定义报表"])


def json_to_response(data: dict) -> dict:
    """Convert datetime strings for Pydantic compatibility"""
    for key, value in data.items():
        if isinstance(value, str) and value in ("None", "null", ""):
            data[key] = None
    return data


@router.get("/tables", response_model=List[TableInfo])
def list_tables():
    """List available data tables"""
    return custom_report_service.get_available_tables()


@router.get("/tables/{table_name}/fields", response_model=List[FieldInfo])
def get_table_fields(table_name: str):
    """Get fields for a specific table"""
    fields = custom_report_service.get_table_fields(table_name)
    if not fields:
        raise HTTPException(status_code=404, detail="表不存在或不支持")
    return fields


@router.post("/preview")
def preview_report(
    request: ReportPreviewRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """Preview report data (limited rows)"""
    config = request.model_dump()
    result = custom_report_service.execute_report(
        db,
        config,
        page=request.page,
        page_size=request.page_size,
    )
    return result


@router.post("", response_model=CustomReportResponse)
def create_report(
    report: CustomReportCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """Save a new report template"""
    # Clean invalid fields (for migrating old configs)
    config = custom_report_service.clean_invalid_fields(report.config.model_dump())

    # Validate config
    is_valid, error = custom_report_service.validate_config(config)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)

    template_id = custom_report_service.save_template(
        db,
        name=report.name,
        config=config,
        description=report.description,
        is_public=report.is_public,
        created_by=current_user.username,
    )

    template = custom_report_service.get_template(db, template_id)
    return json_to_response(template)


@router.get("", response_model=List[CustomReportResponse])
def list_reports(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """List user's report templates"""
    templates = custom_report_service.list_templates(db, current_user.username, include_public=True)
    return [json_to_response(t) for t in templates]


@router.get("/{template_id}", response_model=CustomReportResponse)
def get_report(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """Get a specific report template"""
    template = custom_report_service.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="报表不存在")
    return json_to_response(template)


@router.put("/{template_id}", response_model=CustomReportResponse)
def update_report(
    template_id: int,
    report: CustomReportUpdate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """Update a report template"""
    # Check ownership
    template = custom_report_service.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="报表不存在")
    if template["created_by"] != current_user.username:
        raise HTTPException(status_code=403, detail="无权限修改此报表")

    updates = {}
    if report.name is not None:
        updates["name"] = report.name
    if report.description is not None:
        updates["description"] = report.description
    if report.config is not None:
        # Clean and validate config
        config = custom_report_service.clean_invalid_fields(report.config.model_dump())
        is_valid, error = custom_report_service.validate_config(config)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error)
        updates["config"] = config
    if report.is_public is not None:
        updates["is_public"] = report.is_public

    if updates:
        custom_report_service.update_template(db, template_id, **updates)

    template = custom_report_service.get_template(db, template_id)
    return json_to_response(template)


@router.delete("/{template_id}")
def delete_report(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """Delete a report template"""
    # Check ownership
    template = custom_report_service.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="报表不存在")
    if template["created_by"] != current_user.username:
        raise HTTPException(status_code=403, detail="无权限删除此报表")

    custom_report_service.delete_template(db, template_id)
    return {"message": "删除成功"}


@router.post("/{template_id}/execute")
def execute_report(
    template_id: int,
    request: ReportExecuteRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """Execute a saved report template"""
    template = custom_report_service.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="报表不存在")

    result = custom_report_service.execute_report(
        db,
        template["config"],
        page=request.page,
        page_size=request.page_size,
    )
    return result


@router.post("/{template_id}/export")
def export_report(
    template_id: int,
    request: ReportExportRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """Export report as CSV/Excel"""
    template = custom_report_service.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="报表不存在")

    result = custom_report_service.export_report(
        db,
        template["config"],
        format=request.format,
    )
    return result


@router.post("/{template_id}/share")
def share_report(
    template_id: int,
    share: CustomReportShare,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """Share a report template"""
    # Check ownership
    template = custom_report_service.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="报表不存在")
    if template["created_by"] != current_user.username:
        raise HTTPException(status_code=403, detail="无权限分享此报表")

    custom_report_service.share_template(
        db,
        template_id,
        target_users=share.target_users,
        target_roles=share.target_roles,
    )
    return {"message": "分享成功"}
