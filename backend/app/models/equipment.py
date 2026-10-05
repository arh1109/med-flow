from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import EquipmentStatus

if TYPE_CHECKING:
    from .hospital import Hospital
    from .work_order import WorkOrder


class Equipment(Base):
    __tablename__ = "equipments"

    id: Mapped[int] = mapped_column(primary_key=True)

    serial_number: Mapped[str] = mapped_column(
        String(50),
        index=True,
    )

    model: Mapped[str] = mapped_column(
        String(100),
        index=True,
    )

    status: Mapped[EquipmentStatus] = mapped_column(
        SqlEnum(
            EquipmentStatus,
            name="equipment_status",
            values_callable=lambda enum_cls: [
                member.value
                for member in enum_cls
            ],
        ),
        default=EquipmentStatus.AVAILABLE,
        index=True,
    )
    # Nullable so deleting a hospital can preserve the equipment record.
    hospital_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("hospitals.id"),
        nullable=True,
        index=True,
    )

    battery_level: Mapped[Decimal] = mapped_column(
        Numeric(5, 2)
    )



    hospital: Mapped["Hospital | None"] = relationship(
        back_populates="equipments"
    )

    work_orders: Mapped[list["WorkOrder"]] = relationship(
        back_populates="equipment"
    )

    LOW_CHARGE_LEVEL: int = 20

    def is_low_charge(
        self,
        threshold: int | None = None,
    ) -> bool:
        limit = (
            threshold
            if threshold is not None
            else Equipment.LOW_CHARGE_LEVEL
        )
        return self.battery_level < limit

    def needs_maintenance(self) -> bool:
        return self.status == EquipmentStatus.MAINTENANCE

    def __repr__(self) -> str:
        return (
            f"Equipment(serial={self.serial_number!r}, "
            f"model={self.model!r}, "
            f"Battery={self.battery_level}%, "
            f"status={self.status.value})"
        )
