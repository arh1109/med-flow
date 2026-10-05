from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EquipmentStatus


class EquipmentBase(BaseModel):
    serial_number: str = Field(min_length=1, max_length=50)
    model: str = Field(min_length=1, max_length=100)
    battery_level: Decimal = Field(ge=0, le=100)
    hospital_id: int | None = None
    status: EquipmentStatus = EquipmentStatus.AVAILABLE


class EquipmentCreate(EquipmentBase):
    pass


class EquipmentRead(EquipmentBase):
    id: int
    work_order_ids: list[int] = []
    technician_ids: list[int] = []

    model_config = ConfigDict(from_attributes=True)


class EquipmentUpdate(EquipmentBase):
    pass
