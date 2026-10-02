from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped,  mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .technician import Technician
    from .equipment import Equipment

class Hospital(Base):
    __tablename__ = "hospitals"

    id: Mapped[int] = mapped_column(primary_key = True)
    name: Mapped[str] = mapped_column(String(100))
    location_region: Mapped[str] = mapped_column(String(50))
    capacity: Mapped[int] = mapped_column(Integer)
    supervisor_id: Mapped[int] = mapped_column(Integer)

    equipments: Mapped[list["Equipment"]] = relationship(back_populates="hospital")
    technicians: Mapped[list["Technician"]] = relationship(back_populates="hospital")

    def __repr__(self) -> str:
        return (f"Branch(id={self.id}, name={self.name!r}, "
                f"region={self.location_region!r})")