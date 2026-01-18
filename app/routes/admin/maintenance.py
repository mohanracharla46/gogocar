"""
Admin routes for maintenance and damage management
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.db.models import MaintenanceLog, DamageReport, Cars
from app.routes.admin.dependencies import require_admin
from app.schemas.maintenance import (
    MaintenanceResponse,
    MaintenanceCreate,
    MaintenanceUpdate,
    DamageReportResponse,
    DamageReportCreate,
    DamageReportUpdate
)
from app.utils.pagination import PaginatedResponse
from app.core.logging_config import logger

router = APIRouter(
    prefix="/admin/api/maintenance",
    tags=["admin-maintenance"]
)


def enrich_maintenance(log: MaintenanceLog) -> MaintenanceResponse:
    """Helper to enrich maintenance log response with car info"""
    response = MaintenanceResponse.model_validate(log)
    data = response.model_dump()
    if log.car:
        data["car_brand"] = log.car.brand
        data["car_model"] = log.car.car_model
        data["car_registration"] = log.car.registration_number
    return MaintenanceResponse(**data)


def enrich_damage(report: DamageReport) -> DamageReportResponse:
    """Helper to enrich damage report response with car/order info"""
    response = DamageReportResponse.model_validate(report)
    data = response.model_dump()
    if report.car:
        data["car_brand"] = report.car.brand
        data["car_model"] = report.car.car_model
        data["car_registration"] = report.car.registration_number
    if report.order:
        data["order_reference"] = f"Order #{report.order.id}"
    return DamageReportResponse(**data)


@router.get("/logs", response_model=PaginatedResponse[MaintenanceResponse])
async def list_maintenance_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    car_id: Optional[int] = None,
    maintenance_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """List maintenance logs with optional filters"""
    query = db.query(MaintenanceLog).options(joinedload(MaintenanceLog.car))
    if car_id:
        query = query.filter(MaintenanceLog.car_id == car_id)
    if maintenance_type:
        query = query.filter(MaintenanceLog.maintenance_type == maintenance_type)

    total = query.count()
    logs = (
        query.order_by(MaintenanceLog.start_date.desc(), MaintenanceLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [enrich_maintenance(log) for log in logs]

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
        has_next=page * page_size < total,
        has_prev=page > 1
    )


@router.post("/logs", response_model=MaintenanceResponse, status_code=status.HTTP_201_CREATED)
async def create_maintenance_log(
    maintenance_data: MaintenanceCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Create maintenance log"""
    car = db.query(Cars).filter(Cars.id == maintenance_data.car_id).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")

    log = MaintenanceLog(
        car_id=maintenance_data.car_id,
        maintenance_type=maintenance_data.maintenance_type,
        title=maintenance_data.title,
        description=maintenance_data.description,
        cost=maintenance_data.cost,
        start_date=maintenance_data.start_date,
        end_date=maintenance_data.end_date,
        service_provider=maintenance_data.service_provider,
        created_by=current_user["user_id"]
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    logger.info("Maintenance log %s created by admin %s", log.id, current_user["user_id"])
    return enrich_maintenance(log)


@router.put("/logs/{log_id}", response_model=MaintenanceResponse)
async def update_maintenance_log(
    log_id: int,
    maintenance_data: MaintenanceUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Update maintenance log"""
    log = db.query(MaintenanceLog).filter(MaintenanceLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Maintenance log not found")

    for field, value in maintenance_data.dict(exclude_unset=True).items():
        setattr(log, field, value)

    db.commit()
    db.refresh(log)
    logger.info("Maintenance log %s updated by admin %s", log_id, current_user["user_id"])
    return enrich_maintenance(log)


@router.delete("/logs/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_maintenance_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Delete maintenance log"""
    log = db.query(MaintenanceLog).filter(MaintenanceLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Maintenance log not found")

    db.delete(log)
    db.commit()
    logger.info("Maintenance log %s deleted by admin %s", log_id, current_user["user_id"])
    return None


@router.get("/damages", response_model=PaginatedResponse[DamageReportResponse])
async def list_damage_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    car_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """List damage reports"""
    query = db.query(DamageReport).options(joinedload(DamageReport.car), joinedload(DamageReport.order))
    if car_id:
        query = query.filter(DamageReport.car_id == car_id)
    if status_filter:
        query = query.filter(DamageReport.repair_status == status_filter)

    total = query.count()
    reports = (
        query.order_by(DamageReport.created_at.desc(), DamageReport.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [enrich_damage(report) for report in reports]

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
        has_next=page * page_size < total,
        has_prev=page > 1
    )


@router.get("/damages/{report_id}", response_model=DamageReportResponse)
async def get_damage_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get single damage report"""
    report = db.query(DamageReport).options(joinedload(DamageReport.car), joinedload(DamageReport.order)).filter(DamageReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Damage report not found")
    return enrich_damage(report)


@router.post("/damages", response_model=DamageReportResponse, status_code=status.HTTP_201_CREATED)
async def create_damage_report(
    damage_data: DamageReportCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Create damage report"""
    car = db.query(Cars).filter(Cars.id == damage_data.car_id).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")

    report = DamageReport(
        car_id=damage_data.car_id,
        order_id=damage_data.order_id,
        reported_by=current_user["user_id"],
        damage_description=damage_data.damage_description,
        repair_cost=damage_data.repair_cost
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    logger.info("Damage report %s created by admin %s", report.id, current_user["user_id"])
    return enrich_damage(report)


@router.put("/damages/{report_id}", response_model=DamageReportResponse)
async def update_damage_report(
    report_id: int,
    damage_data: DamageReportUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Update damage report"""
    report = db.query(DamageReport).filter(DamageReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Damage report not found")

    update_fields = damage_data.dict(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(report, field, value)

    # Set repaired_at timestamp when status changes to REPAIRED
    if 'repair_status' in update_fields:
        new_status = update_fields['repair_status'].upper() if update_fields['repair_status'] else None
        if new_status == "REPAIRED" and not report.repaired_at:
            from datetime import datetime
            report.repaired_at = datetime.now()
        elif new_status != "REPAIRED":
            # Clear repaired_at if status is changed from REPAIRED to something else
            report.repaired_at = None

    db.commit()
    db.refresh(report)
    logger.info("Damage report %s updated by admin %s", report_id, current_user["user_id"])
    return enrich_damage(report)


@router.delete("/damages/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_damage_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Delete damage report"""
    report = db.query(DamageReport).filter(DamageReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Damage report not found")

    db.delete(report)
    db.commit()
    logger.info("Damage report %s deleted by admin %s", report_id, current_user["user_id"])
    return None

