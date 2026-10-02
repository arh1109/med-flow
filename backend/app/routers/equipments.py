"""
RoboPulse Fleet Command Center
Day 4 - Robot endpoints.
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, require_role
from app.models import Equipment, EquipmentStatus, User, UserRole
from app.schemas.equipment import EquipmentRead, EquipmentCreate, EquipmentUpdate

#our FastAPI router for the /robots endpoints. The prefix argument means that
#  all routes defined in this router will be prefixed with /robots, and the 
# tags argument is used for documentation purposes in the OpenAPI schema.
router = APIRouter(prefix="/equipments", tags=["equipments"])


#our GET /robots endpoint, which returns a list of robots, optionally filtered by battery level.
@router.get("", response_model=list[EquipmentRead])
async def list_equipments(
    max_battery: Decimal | None = Query(
        default=None,
        ge=0,
        le=100,
        description="Only return equipments strictly below this battery percentage.",
    ),
    db: AsyncSession = Depends(get_db),
    # Day 5 Addition here:
    _: User = Depends(get_current_user)
) -> list[Equipment]:
    """
    Business Question #1: Low Battery Alert - a fourth time.
    GET /robots?max_battery=20 answers the exact same question
    Day 1's Python, Day 2's SQL, and Day 3's ORM query already
    answered - now reachable over HTTP, with the threshold supplied
    by whoever calls the API instead of hardcoded in a script.
    """
    statement = select(Equipment).where(Equipment.status != EquipmentStatus.OFFLINE)
    if max_battery is not None:
        statement = statement.where(Equipment.battery_level < max_battery)
    statement = statement.order_by(Equipment.id)

    result = await db.execute(statement)
    return list(result.scalars().all())

#our GET /robots/{robot_id} endpoint, which returns a single robot by ID.
@router.get("/{equipment_id}", response_model=EquipmentRead)
# Day 5 Addition
async def get_equipment(equipment_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)) -> Equipment:
    equipment = await db.get(Equipment, equipment_id)
    if equipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment {equipment_id} not found",
        )
    return equipment

#our POST /robots endpoint, which creates a new robot.
@router.post("", response_model=EquipmentRead, status_code=status.HTTP_201_CREATED)
async def create_equipment(payload: EquipmentCreate, db: AsyncSession = Depends(get_db),
        # Day 5 Addition
        _: User = Depends(require_role(UserRole.CLINICAL_ADMIN))) -> Equipment:
    equipment = Equipment(**payload.model_dump())
    db.add(equipment)
    await db.commit()
    await db.refresh(equipment)
    return equipment

@router.put("/{equipment_id}", response_model=EquipmentRead)
async def update_equipment(
    equipment_id: int,
    payload: EquipmentUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.CLINICAL_ADMIN)),
) -> Equipment:

    equipment = await db.get(Equipment, equipment_id)

    if equipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment {equipment_id} not found",
        )

    equipment.serial_number = payload.serial_number
    equipment.model = payload.model
    equipment.battery_level = payload.battery_level
    equipment.status = payload.status
    equipment.hospital_id = payload.hospital_id

    await db.commit()
    await db.refresh(equipment)

    return equipment

@router.delete("/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_equipment(
    equipment_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.CLINICAL_ADMIN)),
) -> None:

    equipment = await db.get(Equipment, equipment_id)

    if equipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment {equipment_id} not found",
        )

    await db.delete(equipment)
    await db.commit()