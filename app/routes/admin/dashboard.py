"""
Admin dashboard routes
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.analytics import DashboardStats
from app.services.analytics_service import analytics_service
from app.routes.admin.dependencies import require_admin

router = APIRouter(
    prefix="/admin/api/dashboard",  # Changed to /admin/api/dashboard to avoid conflict with page routes
    tags=["admin-dashboard"]
)


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get dashboard statistics"""
    return analytics_service.get_dashboard_stats(db, days=days)

