"""
RoboPulse Command Center
Reference implementation - Business Questions #4 and #5. No router
for the Branch resource existed before this; both questions are
Branch-level aggregations, so they share one new router.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models import Hospital, WorkOrder, WorkOrderStatus, Technician, Equipment, EquipmentStatus, User
from app.schemas.hospital import MaintenanceFlag, TechnicianActiveWorkOrders, ReportingLineResult

router = APIRouter(prefix="/hospitals", tags=["hospitals"])


@router.get("/maintenance-flags", response_model=list[MaintenanceFlag])
async def maintenance_flags(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Business Question #4: Maintenance Flags.

    WHERE filters rows BEFORE they're grouped/aggregated; this
    question needs to filter on a value that only exists AFTER
    aggregation (a computed percentage per branch) - that's exactly
    what HAVING is for, and it's the first HAVING clause anywhere in
    this project.
    """
    maintenance_count = func.sum(case((Equipment.status == EquipmentStatus.MAINTENANCE, 1), else_=0))
    total_equipments = func.count(Equipment.id)
    maintenance_pct = maintenance_count * 100.0 / total_equipments

    statement = (
        select(
            Hospital.id.label("hospital_id"),
            Hospital.name.label("hospital_name"),
            total_equipments.label("total_equipments"),
            maintenance_count.label("maintenance_count"),
            maintenance_pct.label("maintenance_percentage"),
        )
        .join(Equipment, Equipment.hospital_id == Hospital.id)
        .group_by(Hospital.id, Hospital.name)
        .having(maintenance_pct > 30)
        .order_by(Hospital.id)
    )
    result = await db.execute(statement)
    return [dict(row) for row in result.mappings().all()]


@router.get("/reporting-lines", response_model=ReportingLineResult)
async def reporting_lines(
    supervisor_id: int = Query(..., description="Regional Supervisor's ID (Branch.supervisor_id)."),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Business Question #5: Reporting Lines.

    "Active" mirrors the same definition used everywhere else in this
    project: not yet Completed or Failed - i.e. Pending or
    In-Progress. supervisor_id is deliberately a query parameter, not
    a path parameter tied to a real resource - Day 2's schema.sql
    never modeled supervisors/employees as their own table, so
    supervisor_id is just a plain integer on Branch with nothing to
    look up by ID.
    """
    statement = (
        select(
            Technician.id.label("technician_id"),
            Technician.name.label("technician_name"),
            func.count(WorkOrder.id).label("active_work_order_count"),
        )
        .join(Hospital, Hospital.id == Technician.hospital_id)
        .join(WorkOrder, WorkOrder.technician_id == Technician.id)
        .where(
            Hospital.supervisor_id == supervisor_id,
            WorkOrder.status.in_([WorkOrderStatus.PENDING, WorkOrderStatus.IN_PROGRESS]),
        )
        .group_by(Technician.id, Technician.name)
        .order_by(Technician.id)
    )
    result = await db.execute(statement)
    technicians = [TechnicianActiveWorkOrders(**row) for row in result.mappings().all()]

    return ReportingLineResult(
        supervisor_id=supervisor_id,
        technician_count=len(technicians),
        technicians=technicians,
    )