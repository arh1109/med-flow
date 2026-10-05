from pydantic import BaseModel, ConfigDict, Field


class HospitalBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    location_region: str = Field(min_length=1, max_length=50)
    capacity: int = Field(ge=0)
    supervisor_id: int


class HospitalCreate(HospitalBase):
    pass


class HospitalUpdate(HospitalBase):
    """
    Hospital ID is deliberately absent.

    PUT /hospitals/{hospital_id} updates editable fields while preserving
    the database primary key.
    """


class HospitalRead(HospitalBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class MaintenanceFlag(BaseModel):
    hospital_id: int
    hospital_name: str
    total_equipments: int
    maintenance_count: int
    maintenance_percentage: float


class TechnicianActiveWorkOrders(BaseModel):
    technician_id: int
    technician_name: str
    active_work_order_count: int


class ReportingLineResult(BaseModel):
    supervisor_id: int
    technician_count: int
    technicians: list[TechnicianActiveWorkOrders]
