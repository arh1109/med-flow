from pydantic import BaseModel, ConfigDict

from app.models import WorkOrderPriority, WorkOrderStatus


class WorkOrderStatusUpdate(BaseModel):
    status: WorkOrderStatus


class WorkOrderRead(BaseModel):
    id: int
    title: str
    priority: WorkOrderPriority
    status: WorkOrderStatus
    equipment_id: int
    technician_id: int

    # Newest diagnostic report, folded into the paged row query.
    diagnostic_log_id: int | None = None
    diagnostic_file_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DiscrepancyRead(BaseModel):
    work_order_id: int
    title: str
    equipment_hospital_id: int
    technician_hospital_id: int

    model_config = ConfigDict(from_attributes=True)


class ReliabilityMetric(BaseModel):
    model: str
    total_work_orders: int
    completed_count: int
    failed_count: int


class WorkOrderCreate(BaseModel):
    title: str
    priority: WorkOrderPriority
    status: WorkOrderStatus = WorkOrderStatus.PENDING
    equipment_id: int
    technician_id: int


class WorkOrderUpdate(BaseModel):
    title: str
    priority: WorkOrderPriority
    status: WorkOrderStatus
    equipment_id: int
    technician_id: int
