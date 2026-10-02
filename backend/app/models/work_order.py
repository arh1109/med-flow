from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import WorkOrderPriority, WorkOrderStatus

if TYPE_CHECKING:
    from .diagnostic_log import DiagnosticLog
    from .technician import Technician
    from .equipment import Equipment


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id: Mapped[int] = mapped_column(primary_key = True)

    title: Mapped[str]= mapped_column(String(150))
    priority: Mapped[WorkOrderPriority] = mapped_column(
        SqlEnum(
            WorkOrderPriority,
            name="work_order_priority",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        )
    )
    status: Mapped[WorkOrderStatus] = mapped_column(
        SqlEnum(
            WorkOrderStatus,
            name="work_order_status",
            values_callable = lambda enum_cls: [member.value for member in enum_cls]
        ),
        default = WorkOrderStatus.PENDING
    )
    equipment_id: Mapped[int] = mapped_column(Integer, ForeignKey("equipments.id"))
    technician_id: Mapped[int] = mapped_column(Integer, ForeignKey("technicians.id"))

    equipment: Mapped["Equipment"] = relationship(back_populates="work_orders")
    technician: Mapped["Technician"] = relationship(back_populates="work_orders")
    diagnostic_logs: Mapped[list["DiagnosticLog"]] = relationship(back_populates="work_order")

    def mark_completed(self) -> None:
        self.status = WorkOrderStatus.COMPLETED

    def mark_failed(self) -> None:
        self.status = WorkOrderStatus.FAILED

    def __repr__(self) -> str:
        return (f"Work Order id={self.id}, title={self.title},"
                f"priority={self.priority.value}, status={self.status.value})")