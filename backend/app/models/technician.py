from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .hospital import Hospital
    from .work_order import WorkOrder
    from .user import User


class Technician(Base):
    __tablename__ = "technicians"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[int] = mapped_column(String(100))

    hospital_id: Mapped[int] = mapped_column(Integer, ForeignKey("hospitals.id"))

    hospital: Mapped["Hospital"] = relationship(back_populates="technicians")
    work_orders: Mapped[list["WorkOrder"]] = relationship(back_populates="technician")
    user: Mapped["User | None"] = relationship(
        back_populates="technician"
    )

    def __repr__(self) -> str:
        return (f"Technician(id={self.id}, name={self.name!r}, "
                f"hospital_id={self.hospital_id}")