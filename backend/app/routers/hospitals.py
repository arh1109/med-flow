"""
Hospital CRUD + existing hospital-level reporting routes.

Read access:
- Clinical Admin
- Field Technician
- Auditor

Write access:
- Clinical Admin only

Hospital IDs are immutable. Deleting a hospital preserves associated Equipment
and Technician records by setting their hospital_id values to NULL.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, require_role
from app.models import (
    Equipment,
    EquipmentStatus,
    Hospital,
    Technician,
    User,
    UserRole,
    WorkOrder,
    WorkOrderStatus,
)
from app.schemas.hospital import (
    HospitalCreate,
    HospitalRead,
    HospitalUpdate,
    MaintenanceFlag,
    ReportingLineResult,
    TechnicianActiveWorkOrders,
)


router = APIRouter(
    prefix="/hospitals",
    tags=["hospitals"],
)


# ---------------------------------------------------------------------------
# Hospital resource CRUD
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=list[HospitalRead],
)
async def list_hospitals(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Hospital]:
    statement = (
        select(Hospital)
        .order_by(Hospital.id)
    )

    result = await db.execute(statement)

    return list(result.scalars().all())


@router.post(
    "",
    response_model=HospitalRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_hospital(
    payload: HospitalCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(
        require_role(UserRole.CLINICAL_ADMIN)
    ),
) -> Hospital:
    hospital = Hospital(
        **payload.model_dump()
    )

    db.add(hospital)

    await db.commit()
    await db.refresh(hospital)

    return hospital


# ---------------------------------------------------------------------------
# Existing hospital reports
#
# Keep these static paths ABOVE /{hospital_id} so route matching never treats
# "maintenance-flags" or "reporting-lines" as a hospital ID.
# ---------------------------------------------------------------------------

@router.get(
    "/maintenance-flags",
    response_model=list[MaintenanceFlag],
)
async def maintenance_flags(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.CLINICAL_ADMIN, UserRole.AUDITOR)),
):
    maintenance_count = func.sum(
        case(
            (
                Equipment.status
                == EquipmentStatus.MAINTENANCE,
                1,
            ),
            else_=0,
        )
    )

    total_equipments = func.count(
        Equipment.id
    )

    maintenance_pct = (
        maintenance_count
        * 100.0
        / total_equipments
    )

    statement = (
        select(
            Hospital.id.label("hospital_id"),
            Hospital.name.label("hospital_name"),
            total_equipments.label(
                "total_equipments"
            ),
            maintenance_count.label(
                "maintenance_count"
            ),
            maintenance_pct.label(
                "maintenance_percentage"
            ),
        )
        .join(
            Equipment,
            Equipment.hospital_id == Hospital.id,
        )
        .group_by(
            Hospital.id,
            Hospital.name,
        )
        .having(
            maintenance_pct > 30
        )
        .order_by(
            Hospital.id
        )
    )

    result = await db.execute(statement)

    return [
        dict(row)
        for row
        in result.mappings().all()
    ]


@router.get(
    "/reporting-lines",
    response_model=ReportingLineResult,
)
async def reporting_lines(
    supervisor_id: int = Query(
        ...,
        description=(
            "Regional Supervisor's ID "
            "(Hospital.supervisor_id)."
        ),
    ),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.CLINICAL_ADMIN, UserRole.AUDITOR)),
):
    statement = (
        select(
            Technician.id.label(
                "technician_id"
            ),
            Technician.name.label(
                "technician_name"
            ),
            func.count(
                WorkOrder.id
            ).label(
                "active_work_order_count"
            ),
        )
        .join(
            Hospital,
            Hospital.id
            == Technician.hospital_id,
        )
        .join(
            WorkOrder,
            WorkOrder.technician_id
            == Technician.id,
        )
        .where(
            Hospital.supervisor_id
            == supervisor_id,
            WorkOrder.status.in_(
                [
                    WorkOrderStatus.PENDING,
                    WorkOrderStatus.IN_PROGRESS,
                ]
            ),
        )
        .group_by(
            Technician.id,
            Technician.name,
        )
        .order_by(
            Technician.id
        )
    )

    result = await db.execute(statement)

    technicians = [
        TechnicianActiveWorkOrders(**row)
        for row
        in result.mappings().all()
    ]

    return ReportingLineResult(
        supervisor_id=supervisor_id,
        technician_count=len(technicians),
        technicians=technicians,
    )


@router.get(
    "/{hospital_id}",
    response_model=HospitalRead,
)
async def get_hospital(
    hospital_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Hospital:
    hospital = await db.get(
        Hospital,
        hospital_id,
    )

    if hospital is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Hospital {hospital_id} "
                "not found"
            ),
        )

    return hospital


@router.put(
    "/{hospital_id}",
    response_model=HospitalRead,
)
async def update_hospital(
    hospital_id: int,
    payload: HospitalUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(
        require_role(UserRole.CLINICAL_ADMIN)
    ),
) -> Hospital:
    hospital = await db.get(
        Hospital,
        hospital_id,
    )

    if hospital is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Hospital {hospital_id} "
                "not found"
            ),
        )

    # ID is intentionally never changed.
    hospital.name = payload.name
    hospital.location_region = (
        payload.location_region
    )
    hospital.capacity = payload.capacity
    hospital.supervisor_id = (
        payload.supervisor_id
    )

    await db.commit()
    await db.refresh(hospital)

    return hospital


@router.delete(
    "/{hospital_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_hospital(
    hospital_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(
        require_role(UserRole.CLINICAL_ADMIN)
    ),
) -> None:
    hospital = await db.get(
        Hospital,
        hospital_id,
    )

    if hospital is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Hospital {hospital_id} "
                "not found"
            ),
        )

    # WorkOrder has no hospital_id column in the current schema.
    # Preserve Equipment and Technician rows by detaching them first.
    await db.execute(
        update(Equipment)
        .where(
            Equipment.hospital_id
            == hospital_id
        )
        .values(
            hospital_id=None
        )
    )

    await db.execute(
        update(Technician)
        .where(
            Technician.hospital_id
            == hospital_id
        )
        .values(
            hospital_id=None
        )
    )

    await db.delete(hospital)
    await db.commit()
