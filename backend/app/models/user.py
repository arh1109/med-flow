
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import UserRole

if TYPE_CHECKING:
    from .technician import Technician


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255)
    )

    role: Mapped[UserRole] = mapped_column(
        SqlEnum(
            UserRole,
            name="user_role",
            values_callable=lambda enum_cls: [
                member.value for member in enum_cls
            ],
        )
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    technician_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("technicians.id"),
        nullable=True,
        unique=True,
    )

    technician: Mapped["Technician | None"] = relationship(
        back_populates="user"
    )

    def __repr__(self) -> str:
        return (
            f"User(id={self.id}, "
            f"username={self.username!r}, "
            f"role={self.role.value}, "
            f"technician_id={self.technician_id})"
        )