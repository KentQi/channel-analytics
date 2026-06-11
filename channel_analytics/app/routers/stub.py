"""
Stub routers for future implementation.
Placeholder endpoints for channels, analytics, reports, wholesale.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db


# Channel-related endpoints
channels_router = APIRouter(prefix="/channels", tags=["channels"])


@channels_router.get("/")
async def list_channels(db: Session = Depends(get_db)):
    """List all channels - stub implementation."""
    return {"message": "Not implemented yet"}


@channels_router.get("/{channel_id}")
async def get_channel(channel_id: int, db: Session = Depends(get_db)):
    """Get channel details - stub implementation."""
    return {"message": f"Channel {channel_id} not implemented yet"}


# Analytics-related endpoints
analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])


@analytics_router.get("/overview")
async def get_analytics_overview(db: Session = Depends(get_db)):
    """Get analytics overview - stub implementation."""
    return {"message": "Analytics overview not implemented yet"}


@analytics_router.get("/trend")
async def get_analytics_trend(db: Session = Depends(get_db)):
    """Get analytics trend - stub implementation."""
    return {"message": "Analytics trend not implemented yet"}


# Reports-related endpoints
reports_router = APIRouter(prefix="/reports", tags=["reports"])


@reports_router.get("/")
async def list_reports(db: Session = Depends(get_db)):
    """List all reports - stub implementation."""
    return {"message": "Reports listing not implemented yet"}


@reports_router.get("/{report_id}")
async def get_report(report_id: int, db: Session = Depends(get_db)):
    """Get report details - stub implementation."""
    return {"message": f"Report {report_id} not implemented yet"}


# Wholesale-related endpoints
wholesale_router = APIRouter(prefix="/wholesale", tags=["wholesale"])


@wholesale_router.get("/stats")
async def get_wholesale_stats(db: Session = Depends(get_db)):
    """Get wholesale statistics - stub implementation."""
    return {"message": "Wholesale stats not implemented yet"}
