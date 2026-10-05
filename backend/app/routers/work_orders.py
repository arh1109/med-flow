from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select, case, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, require_role
from app.models import WorkOrder, WorkOrderPriority, Technician, Equipment, WorkOrderStatus, User, UserRole
from app.schemas.work_order import (
    DiscrepancyRead,
    WorkOrderCreate,
    WorkOrderRead,
    WorkOrderStatusUpdate,
    WorkOrderUpdate,
    ReliabilityMetric,
)
from typing import Annotated
from sqlalchemy import asc, desc, or_
from app.models import DiagnosticLog
from app.schemas.pagination import (
    Page,
    PaginationParams,
    get_pagination_params,
)

router = APIRouter(prefix="/work_orders", tags=["work_orders"])

WORK_ORDER_SORT_COLUMNS = {
    "id": WorkOrder.id,
    "title": WorkOrder.title,
    "priority": WorkOrder.priority,
    "status": WorkOrder.status,
    "equipment_id": WorkOrder.equipment_id,
    "technician_id": WorkOrder.technician_id,
}


@router.get("/discrepancies", response_model=list[DiscrepancyRead])
async def list_colocation_discrepancies(
    priority: WorkOrderPriority | None = Query(
        default=None,
        description="Only return discrepancies for work_orders of this priority.",
    ),
    db: AsyncSession = Depends(get_db),
    ##Day 5 code here
    _: User = Depends(require_role(UserRole.CLINICAL_ADMIN, UserRole.AUDITOR)),
):
    """
    Business Question #2: Co-Location Discrepancy - a fourth time.
    Day 1: Python. Day 2: raw SQL. Day 3: async ORM script. Today:
    the same three-table JOIN, reachable at
    GET /work_orders/discrepancies, with an optional priority filter.

    Selects only the four columns the response actually needs,
    rather than full WorkOrder/Equipment/Technician objects, to reduce 
    the amount of data sent over the wire.
    """
    statement = (
        select(
            WorkOrder.id.label("work_order_id"),
            WorkOrder.title,
            Equipment.hospital_id.label("equipment_hospital_id"),
            Technician.hospital_id.label("technician_hospital_id"),
        )
        .join(Equipment, Equipment.id == WorkOrder.equipment_id)
        .join(Technician, Technician.id == WorkOrder.technician_id)
        .where(Equipment.hospital_id != Technician.hospital_id)
    )

    #if a priority filter was provided, add it to the WHERE clause
    if priority is not None:
        statement = statement.where(WorkOrder.priority == priority)

    statement = statement.order_by(WorkOrder.id)

    result = await db.execute(statement)
    return [dict(row) for row in result.mappings().all()]

@router.patch(
    "/{work_order_id}/status",
    response_model=WorkOrderRead,
)
async def update_work_order_status(
    work_order_id: int,
    payload: WorkOrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(
            UserRole.FIELD_TECHNICIAN
        )
    ),
) -> WorkOrder:

    if current_user.technician_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Field Technician account is not "
                "linked to a technician"
            ),
        )

    work_order = await db.get(
        WorkOrder,
        work_order_id,
    )

    if work_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Work Order {work_order_id} "
                "not found"
            ),
        )

    if (
        work_order.technician_id
        != current_user.technician_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You may only update work orders "
                "assigned to you"
            ),
        )

    work_order.status = payload.status

    await db.commit()
    await db.refresh(work_order)

    return work_order


@router.get("/reliability", response_model=list[ReliabilityMetric])
async def reliability_metrics(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.CLINICAL_ADMIN, UserRole.AUDITOR)),
):
    """
    Business Question #3: Reliability Metrics.
    Any authenticated role can view this - it's an analytics endpoint,
    matching the problem statement's "Auditor can view analytics
    dashboards" requirement, same as /work_orders/discrepancies.
    """
    statement = (
        select(
            Equipment.model,
            func.count(WorkOrder.id).label("total_work_orders"),
            func.sum(case((WorkOrder.status == WorkOrderStatus.COMPLETED, 1), else_=0)).label("completed_count"),
            func.sum(case((WorkOrder.status == WorkOrderStatus.FAILED, 1), else_=0)).label("failed_count"),
        )
        .join(WorkOrder, WorkOrder.equipment_id == Equipment.id)
        .group_by(Equipment.model)
        .order_by(Equipment.model)
    )
    result = await db.execute(statement)
    return [dict(row) for row in result.mappings().all()]

def _work_order_sort_expression(
    pagination: PaginationParams,
):
    column = WORK_ORDER_SORT_COLUMNS.get(
        pagination.sort_by
    )

    if column is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Invalid sort_by. Allowed values: "
                + ", ".join(
                    WORK_ORDER_SORT_COLUMNS.keys()
                )
            ),
        )

    return (
        desc(column)
        if pagination.sort_dir == "desc"
        else asc(column)
    )


@router.get(
    "",
    response_model=Page[WorkOrderRead],
)
async def list_work_orders(
    pagination: Annotated[
        PaginationParams,
        Depends(get_pagination_params),
    ],
    work_order_status: WorkOrderStatus | None = Query(
        default=None,
        alias="status",
    ),
    hospital_id: int | None = Query(
        default=None,
        ge=1,
    ),
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
        description=(
            "Case-insensitive search across work-order title, "
            "equipment model, and equipment serial number."
        ),
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
) -> Page[WorkOrderRead]:

    order_by = (
        _work_order_sort_expression(
            pagination
        )
    )

    conditions = []

    if (
        current_user.role
        == UserRole.FIELD_TECHNICIAN
    ):
        if current_user.technician_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Field Technician account is "
                    "not linked to a technician"
                ),
            )

        # This role scope is part of BOTH the count and page query.
        conditions.append(
            WorkOrder.technician_id
            == current_user.technician_id
        )

    if work_order_status is not None:
        conditions.append(
            WorkOrder.status
            == work_order_status
        )

    if hospital_id is not None:
        conditions.append(
            Equipment.hospital_id
            == hospital_id
        )

    if search:
        pattern = f"%{search.strip()}%"

        conditions.append(
            or_(
                WorkOrder.title.ilike(pattern),
                Equipment.model.ilike(pattern),
                Equipment.serial_number.ilike(
                    pattern
                ),
            )
        )

    # Query 1: accurate count after all role/filter predicates.
    count_statement = (
        select(
            func.count(WorkOrder.id)
        )
        .join(
            Equipment,
            Equipment.id
            == WorkOrder.equipment_id,
        )
        .where(*conditions)
    )

    total = (
        await db.execute(count_statement)
    ).scalar_one()

    offset = (
        pagination.page - 1
    ) * pagination.size

    # Correlated scalar subqueries add the newest diagnostic report
    # without loading /diagnostic_logs separately.
    latest_diagnostic_id = (
        select(DiagnosticLog.id)
        .where(
            DiagnosticLog.work_order_id
            == WorkOrder.id
        )
        .order_by(
            DiagnosticLog.created_at.desc(),
            DiagnosticLog.id.desc(),
        )
        .limit(1)
        .correlate(WorkOrder)
        .scalar_subquery()
    )

    latest_diagnostic_file_url = (
        select(DiagnosticLog.file_url)
        .where(
            DiagnosticLog.work_order_id
            == WorkOrder.id
        )
        .order_by(
            DiagnosticLog.created_at.desc(),
            DiagnosticLog.id.desc(),
        )
        .limit(1)
        .correlate(WorkOrder)
        .scalar_subquery()
    )

    # Query 2: one page only, sorted in SQL.
    rows_statement = (
        select(
            WorkOrder.id,
            WorkOrder.title,
            WorkOrder.priority,
            WorkOrder.status,
            WorkOrder.equipment_id,
            WorkOrder.technician_id,
            latest_diagnostic_id.label(
                "diagnostic_log_id"
            ),
            latest_diagnostic_file_url.label(
                "diagnostic_file_url"
            ),
        )
        .join(
            Equipment,
            Equipment.id
            == WorkOrder.equipment_id,
        )
        .where(*conditions)
        .order_by(
            order_by,
            WorkOrder.id.asc(),
        )
        .offset(offset)
        .limit(pagination.size)
    )

    result = await db.execute(
        rows_statement
    )

    items = [
        WorkOrderRead(
            **dict(row)
        )
        for row in result.mappings().all()
    ]

    return Page[WorkOrderRead](
        items=items,
        total=total,
        page=pagination.page,
        size=pagination.size,
    )

@router.post(
    "",
    response_model=WorkOrderRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_work_order(
    payload: WorkOrderCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(
        require_role(UserRole.CLINICAL_ADMIN)
    ),
) -> WorkOrder:

    work_order = WorkOrder(**payload.model_dump())

    db.add(work_order)

    await db.commit()
    await db.refresh(work_order)

    return work_order

@router.put(
    "/{work_order_id}",
    response_model=WorkOrderRead,
)
async def update_work_order(
    work_order_id: int,
    payload: WorkOrderUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(
        require_role(UserRole.CLINICAL_ADMIN)
    ),
) -> WorkOrder:

    work_order = await db.get(WorkOrder, work_order_id)

    if work_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work Order {work_order_id} not found",
        )

    work_order.title = payload.title
    work_order.priority = payload.priority
    work_order.status = payload.status
    work_order.equipment_id = payload.equipment_id
    work_order.technician_id = payload.technician_id

    await db.commit()
    await db.refresh(work_order)

    return work_order

@router.delete(
    "/{work_order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_work_order(
    work_order_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(
        require_role(UserRole.CLINICAL_ADMIN)
    ),
) -> None:

    work_order = await db.get(WorkOrder, work_order_id)

    if work_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work Order {work_order_id} not found",
        )

    await db.delete(work_order)
    await db.commit()