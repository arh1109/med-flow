from pydantic import BaseModel

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