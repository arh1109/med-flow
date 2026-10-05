from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, asc, desc, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, require_role
from app.models import (
    Equipment,
    EquipmentStatus,
    User,
    UserRole,
    WorkOrder,
)
from app.schemas.equipment import (
    EquipmentCreate,
    EquipmentRead,
    EquipmentUpdate,
)
from app.schemas.pagination import (
    Page,
    PaginationParams,
    get_pagination_params,
)


router = APIRouter(
    prefix="/equipments",
    tags=["equipments"],
)


EQUIPMENT_SORT_COLUMNS = {
    "id": Equipment.id,
    "serial_number": Equipment.serial_number,
    "model": Equipment.model,
    "status": Equipment.status,
    "battery_level": Equipment.battery_level,
    "hospital_id": Equipment.hospital_id,
}


def _validate_sort(
    pagination: PaginationParams,
):
    column = EQUIPMENT_SORT_COLUMNS.get(
        pagination.sort_by
    )

    if column is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Invalid sort_by. Allowed values: "
                + ", ".join(
                    EQUIPMENT_SORT_COLUMNS.keys()
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
    response_model=Page[EquipmentRead],
)
async def list_equipments(
    pagination: Annotated[
        PaginationParams,
        Depends(get_pagination_params),
    ],
    equipment_status: EquipmentStatus | None = Query(
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
            "Case-insensitive search across model "
            "and serial number."
        ),
    ),
    max_battery: Decimal | None = Query(
        default=None,
        ge=0,
        le=100,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Page[EquipmentRead]:

    order_by = _validate_sort(
        pagination
    )

    conditions = [
        # Preserve the existing business rule:
        # Offline equipment is not part of this list endpoint.
        Equipment.status
        != EquipmentStatus.OFFLINE
    ]

    if equipment_status is not None:
        conditions.append(
            Equipment.status
            == equipment_status
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
                Equipment.model.ilike(pattern),
                Equipment.serial_number.ilike(
                    pattern
                ),
            )
        )

    if max_battery is not None:
        conditions.append(
            Equipment.battery_level
            < max_battery
        )

    assignment_join_condition = (
        WorkOrder.equipment_id
        == Equipment.id
    )

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

        conditions.append(
            exists(
                select(1).where(
                    WorkOrder.equipment_id
                    == Equipment.id,
                    WorkOrder.technician_id
                    == current_user.technician_id,
                )
            )
        )

        # Only expose assignments belonging to the caller.
        assignment_join_condition = and_(
            assignment_join_condition,
            WorkOrder.technician_id
            == current_user.technician_id,
        )

    # Query 1: count the full filtered result set.
    count_statement = (
        select(
            func.count(Equipment.id)
        )
        .where(*conditions)
    )

    total = (
        await db.execute(count_statement)
    ).scalar_one()

    offset = (
        pagination.page - 1
    ) * pagination.size

    # Query 2: retrieve exactly one page and aggregate related assignment IDs
    # in SQL. This avoids one assignment query per equipment row.
    rows_statement = (
        select(
            Equipment.id,
            Equipment.serial_number,
            Equipment.model,
            Equipment.status,
            Equipment.battery_level,
            Equipment.hospital_id,
            func.array_agg(
                func.distinct(WorkOrder.id)
            )
            .filter(
                WorkOrder.id.is_not(None)
            )
            .label("work_order_ids"),
            func.array_agg(
                func.distinct(
                    WorkOrder.technician_id
                )
            )
            .filter(
                WorkOrder.technician_id.is_not(
                    None
                )
            )
            .label("technician_ids"),
        )
        .outerjoin(
            WorkOrder,
            assignment_join_condition,
        )
        .where(*conditions)
        .group_by(
            Equipment.id,
            Equipment.serial_number,
            Equipment.model,
            Equipment.status,
            Equipment.battery_level,
            Equipment.hospital_id,
        )
        .order_by(
            order_by,
            Equipment.id.asc(),
        )
        .offset(offset)
        .limit(pagination.size)
    )

    result = await db.execute(
        rows_statement
    )

    items = [
        EquipmentRead(
            id=row.id,
            serial_number=row.serial_number,
            model=row.model,
            status=row.status,
            battery_level=row.battery_level,
            hospital_id=row.hospital_id,
            work_order_ids=sorted(
                row.work_order_ids or []
            ),
            technician_ids=sorted(
                row.technician_ids or []
            ),
        )
        for row in result
    ]

    return Page[EquipmentRead](
        items=items,
        total=total,
        page=pagination.page,
        size=pagination.size,
    )


async def _assignment_rows(
    db: AsyncSession,
    equipment_id: int,
    technician_id: int | None = None,
):
    statement = select(
        WorkOrder.id.label("work_order_id"),
        WorkOrder.technician_id.label(
            "technician_id"
        ),
    ).where(
        WorkOrder.equipment_id
        == equipment_id
    )

    if technician_id is not None:
        statement = statement.where(
            WorkOrder.technician_id
            == technician_id
        )

    return list(
        (
            await db.execute(statement)
        ).all()
    )


def _build_equipment_read(
    equipment: Equipment,
    assignment_rows,
) -> EquipmentRead:
    return EquipmentRead(
        id=equipment.id,
        serial_number=equipment.serial_number,
        model=equipment.model,
        battery_level=equipment.battery_level,
        hospital_id=equipment.hospital_id,
        status=equipment.status,
        work_order_ids=sorted(
            {
                row.work_order_id
                for row in assignment_rows
            }
        ),
        technician_ids=sorted(
            {
                row.technician_id
                for row in assignment_rows
            }
        ),
    )


@router.get(
    "/{equipment_id}",
    response_model=EquipmentRead,
)
async def get_equipment(
    equipment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
) -> EquipmentRead:

    equipment = await db.get(
        Equipment,
        equipment_id,
    )

    if equipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Equipment {equipment_id} "
                "not found"
            ),
        )

    technician_filter = None

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

        technician_filter = (
            current_user.technician_id
        )

    assignments = await _assignment_rows(
        db,
        equipment_id,
        technician_filter,
    )

    if (
        current_user.role
        == UserRole.FIELD_TECHNICIAN
        and not assignments
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Equipment {equipment_id} "
                "not found"
            ),
        )

    return _build_equipment_read(
        equipment,
        assignments,
    )


@router.post(
    "",
    response_model=EquipmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_equipment(
    payload: EquipmentCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(
        require_role(
            UserRole.CLINICAL_ADMIN
        )
    ),
) -> EquipmentRead:

    equipment = Equipment(
        **payload.model_dump()
    )

    db.add(equipment)
    await db.commit()
    await db.refresh(equipment)

    return _build_equipment_read(
        equipment,
        [],
    )


@router.put(
    "/{equipment_id}",
    response_model=EquipmentRead,
)
async def update_equipment(
    equipment_id: int,
    payload: EquipmentUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(
        require_role(
            UserRole.CLINICAL_ADMIN
        )
    ),
) -> EquipmentRead:

    equipment = await db.get(
        Equipment,
        equipment_id,
    )

    if equipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Equipment {equipment_id} "
                "not found"
            ),
        )

    for field, value in (
        payload.model_dump()
    ).items():
        setattr(
            equipment,
            field,
            value,
        )

    await db.commit()
    await db.refresh(equipment)

    assignments = await _assignment_rows(
        db,
        equipment.id,
    )

    return _build_equipment_read(
        equipment,
        assignments,
    )


@router.delete(
    "/{equipment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_equipment(
    equipment_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(
        require_role(
            UserRole.CLINICAL_ADMIN
        )
    ),
) -> None:

    equipment = await db.get(
        Equipment,
        equipment_id,
    )

    if equipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Equipment {equipment_id} "
                "not found"
            ),
        )

    await db.delete(equipment)
    await db.commit()
