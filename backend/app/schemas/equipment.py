
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EquipmentStatus

class EquipmentBase(BaseModel):
    serial_number: str = Field(min_length=1, max_length=50)
    model: str= Field(min_length=1, max_length=100)
    battery_level: Decimal = Field(ge=0, le=100)
    hospital_id: int
    status: EquipmentStatus = EquipmentStatus.AVAILABLE

class EquipmentCreate(EquipmentBase):
    """ Shape of the Request Body for POST /equipments """

class EquipmentRead(EquipmentBase):
    """ Shape of the Equipment in any API Response """
    id: int

    model_config = ConfigDict(from_attributes=True)

class EquipmentUpdate(BaseModel):
    serial_number: str
    model: str
    battery_level: Decimal
    hospital_id: int
    status: EquipmentStatus