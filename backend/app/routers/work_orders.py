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

router = APIRouter(prefix="/work_orders", tags=["work_orders"])


@router.get("/discrepancies", response_model=list[DiscrepancyRead])
async def list_colocation_discrepancies(
    priority: WorkOrderPriority | None = Query(
        default=None,
        description="Only return discrepancies for work_orders of this priority.",
    ),
    db: AsyncSession = Depends(get_db),
    ##Day 5 code here
    _: User = Depends(require_role(UserRole.CLINICAL_ADMIN, UserRole.FIELD_TECHNICIAN)),
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
    _: User = Depends(get_current_user),
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

@router.get(
    "",
    response_model=list[WorkOrderRead],
)
async def list_work_orders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WorkOrder]:

    statement = select(WorkOrder)

    if (
        current_user.role
        == UserRole.FIELD_TECHNICIAN
    ):
        if current_user.technician_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Field Technician account is not "
                    "linked to a technician"
                ),
            )

        statement = statement.where(
            WorkOrder.technician_id
            == current_user.technician_id
        )

    statement = statement.order_by(
        WorkOrder.id
    )

    result = await db.execute(statement)

    return list(result.scalars().all())

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